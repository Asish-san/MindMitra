// api/chat.js - Vercel Serverless
// Uses LibreTranslate public instance for detect/translate
// Uses Hugging Face Inference API for generation (HF token required in Vercel env as HF_API_TOKEN)

const LIBRETRANSLATE_BASE = 'https://libretranslate.com';
const HF_MODEL = 'google/flan-t5-base'; // small instruction-following model; swap if you want
const HF_API = process.env.HF_API_TOKEN || ''; // Put your HF token in Vercel env: HF_API_TOKEN

// Crisis detection phrases (English check after translation)
const CRISIS_PATTERNS = [
  'suicide','kill myself','want to die','end my life','hurt myself','self harm','i will die'
];

const CRISIS_MESSAGE_EN = `I'm really sorry you're feeling this much pain. You are not alone. If you are in immediate danger, please contact your local emergency number. In India you can contact the KIRAN helpline at 1800-599-0019. If you can, please reach out to someone you trust and consider contacting a licensed professional.`;

async function jsonPost(url, body) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  return res;
}

async function detectLanguage(text) {
  try {
    const res = await jsonPost(`${LIBRETRANSLATE_BASE}/detect`, { q: text });
    const j = await res.json();
    if (Array.isArray(j) && j.length && j[0].language) return j[0].language;
  } catch (e) {
    // ignore and fallback
  }
  return 'en';
}

async function translate(text, source, target) {
  try {
    const res = await jsonPost(`${LIBRETRANSLATE_BASE}/translate`, {
      q: text,
      source: source || 'auto',
      target,
      format: 'text'
    });
    const j = await res.json();
    if (j && j.translatedText) return j.translatedText;
    // If it returns raw string or other shape
    if (typeof j === 'string') return j;
    return JSON.stringify(j);
  } catch (e) {
    // fallback: return original text if translation fails
    return text;
  }
}

function crisisCheckEnglish(textEn) {
  if (!textEn) return false;
  const low = textEn.toLowerCase();
  return CRISIS_PATTERNS.some(p => low.includes(p));
}

async function generateFromHF(prompt) {
  if (!HF_API) {
    // graceful fallback if HF token not set
    return "I hear you. Thanks for telling me that. If you want, tell me a bit more — where does this feeling show up in your day?";
  }

  // Call Hugging Face Inference API (synchronous)
  try {
    const res = await fetch(`https://api-inference.huggingface.co/models/${HF_MODEL}`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${HF_API}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        inputs: prompt,
        parameters: { max_new_tokens: 200, temperature: 0.7 },
        options: { wait_for_model: true }
      })
    });

    if (!res.ok) {
      const text = await res.text();
      console.error('HF error', res.status, text);
      return null;
    }
    const data = await res.json();
    // Typical responses: [{generated_text: "..."}]
    if (Array.isArray(data) && data[0] && data[0].generated_text) return data[0].generated_text;
    // Sometimes API returns text directly
    if (typeof data === 'string') return data;
    // As a fallback, try JSON shapes
    if (Array.isArray(data) && data[0] && typeof data[0] === 'string') return data[0];
    return JSON.stringify(data);
  } catch (err) {
    console.error('HF call failed', err);
    return null;
  }
}

function makeSystemPrompt() {
  return `You are MindMitra, a calm, empathetic, non-judgmental companion for young people. Keep replies brief (2-5 sentences). Validate feelings, offer a single practical coping tip, and gently suggest seeking support (trusted person or professional) if needed. Do not diagnose or provide medical instructions. Use friendly, plain language.`;
}

export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  try {
    const body = await req.json();
    const message = (body.message || '').toString().trim();
    const requestedLang = (body.lang || '').toString().trim();

    if (!message) return res.status(400).json({ error: 'Empty message' });

    // 1) detect user language
    const detected = await detectLanguage(message);

    // 2) translate to English if needed
    let messageEn = message;
    if (detected && detected !== 'en') {
      messageEn = await translate(message, detected, 'en');
    }

    // 3) crisis check in English text
    const crisis = crisisCheckEnglish(messageEn);
    let replyEn = '';

    if (crisis) {
      replyEn = CRISIS_MESSAGE_EN;
    } else {
      // 4) build final prompt and call generation
      const system = makeSystemPrompt();
      const prompt = `${system}\n\nUser: ${messageEn}\n\nAssistant:`;
      const gen = await generateFromHF(prompt);

      if (gen === null) {
        // generation error -> fallback empathetic reply
        replyEn = "I understand. That sounds difficult. Can you tell me one concrete thing that just happened, or how long you've felt like this?";
      } else {
        replyEn = gen.toString().trim();
      }
    }

    // 5) determine reply language (requestedLang || detected)
    let outLang = requestedLang || detected || 'en';
    if (!outLang) outLang = 'en';

    // If outLang is not English, translate reply back
    let replyOut = replyEn;
    if (outLang !== 'en') {
      replyOut = await translate(replyEn, 'en', outLang);
    }

    return res.json({
      reply: replyOut,
      reply_lang: outLang,
      detected_lang: detected,
      crisis
    });
  } catch (err) {
    console.error('Unhandled error in /api/chat', err);
    return res.status(500).json({ error: 'Server error', details: String(err) });
  }
}
