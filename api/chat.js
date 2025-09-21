// api/chat.js
// Vercel serverless function (Node 18+ runtime)
const LIBRETRANSLATE_BASE = 'https://libretranslate.com';
const HF_MODEL = 'google/flan-t5-base'; // small instruction-following model good for demos
const HF_API = process.env.HF_API_TOKEN; // set in Vercel dashboard (see steps)

function crisisCheck(textEn) {
  if (!textEn) return false;
  const t = textEn.toLowerCase();
  const patterns = [
    'suicide','kill myself','want to die','end my life','hurt myself','self harm','i will die'
  ];
  return patterns.some(p => t.includes(p));
}

async function detectLanguage(text) {
  const res = await fetch(`${LIBRETRANSLATE_BASE}/detect`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ q: text })
  });
  const arr = await res.json();
  if (!arr || !arr.length) return 'en';
  return arr[0].language || 'en';
}

async function translate(text, source, target) {
  if (!text) return text;
  const res = await fetch(`${LIBRETRANSLATE_BASE}/translate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      q: text,
      source: source || 'auto',
      target,
      format: 'text'
    })
  });
  const j = await res.json();
  if (j && j.translatedText) return j.translatedText;
  // fallback if plain string or other shape
  if (typeof j === 'string') return j;
  return JSON.stringify(j);
}

async function hfGenerate(prompt) {
  if (!HF_API) {
    // Safe fallback if token not set
    return `I hear you. Thanks for sharing that. Can you tell me a bit more about what's going on?`;
  }
  const res = await fetch(`https://api-inference.huggingface.co/models/${HF_MODEL}`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${HF_API}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      inputs: prompt,
      parameters: { max_new_tokens: 180, temperature: 0.7 },
      options: { wait_for_model: true }
    })
  });
  if (!res.ok) {
    const text = await res.text();
    console.error('HF error', res.status, text);
    throw new Error('Generation error: ' + res.status);
  }
  const data = await res.json();
  if (Array.isArray(data) && data[0]?.generated_text) return data[0].generated_text;
  if (Array.isArray(data) && data[0]?.generated_text === undefined && data[0]?.generated_text !== undefined) {
    return data[0].generated_text;
  }
  // fallback shapes
  if (typeof data === 'object' && data[0] && data[0].generated_text) return data[0].generated_text;
  if (typeof data === 'string') return data;
  return JSON.stringify(data);
}

export default async function handler(req, res) {
  try {
    if (req.method !== 'POST') return res.status(405).send({ error: 'Method not allowed' });
    const { message, lang } = req.body || {};
    if (!message || typeof message !== 'string' || message.trim().length === 0)
      return res.status(400).json({ error: 'Empty message' });

    // 1) detect language (LibreTranslate)
    const detected = await detectLanguage(message);

    // 2) translate to English if needed
    let textEn = message;
    if (detected && detected !== 'en') {
      try { textEn = await translate(message, detected, 'en'); } catch (e) { textEn = message; }
    }

    // 3) crisis check
    const crisis = crisisCheck(textEn);
    let replyEn;
    if (crisis) {
      replyEn = `I'm really sorry you're feeling this much pain. If you are in immediate danger, please contact your local emergency number. In India you can call KIRAN on 1800-599-0019. If possible, reach out to someone you trust and consider contacting a licensed professional.`;
    } else {
      // build instruction prompt
      const system = `You are MindMitra, an empathetic, non-judgmental youth support assistant. Keep responses short (2-5 sentences), validating and practical. Offer one simple coping tip and suggest seeking support if needed. Do not provide clinical diagnosis.`;
      const prompt = `${system}\n\nUser: ${textEn}\n\nAssistant:`;
      replyEn = await hfGenerate(prompt);
      replyEn = (replyEn || '').trim();
    }

    // 4) choose output language: user requested `lang` or detected language
    const outLang = (lang && lang.length) ? lang : detected || 'en';
    let replyOut = replyEn;
    if (outLang && outLang !== 'en') {
      try { replyOut = await translate(replyEn, 'en', outLang); } catch (e) { replyOut = replyEn; }
    }

    // 5) return (no storage, do not save PII)
    return res.json({
      reply: replyOut,
      reply_lang: outLang,
      detected_lang: detected,
      crisis
    });

  } catch (err) {
    console.error('Server error', err);
    return res.status(500).json({ error: 'Server error' });
  }
}
