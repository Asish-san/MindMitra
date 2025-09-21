# app.py
import streamlit as st
import requests
import html
import time

# ---------------------------
# Config
# ---------------------------
LIBRETRANSLATE_BASE = "https://libretranslate.com"
HF_MODEL = "google/flan-t5-base"  # small instruction-following model, good for demo
# Hugging Face token MUST be injected as a secret in Spaces (HF_API_TOKEN)
HF_API_TOKEN = st.secrets.get("HF_API_TOKEN", "")  # empty string fallback
# Crisis helpline text (India example). Update before public mass release.
CRISIS_HELPLINE = "If you are in immediate danger, contact local emergency services. In India you can contact KIRAN at 1800-599-0019."

CRISIS_PATTERNS = [
    "suicide",
    "kill myself",
    "want to die",
    "end my life",
    "hurt myself",
    "self harm",
    "i will die",
    "i'll die",
    "i'm going to kill myself",
]


# ---------------------------
# Helper functions
# ---------------------------
def json_post(url: str, body: dict, headers: dict = None, timeout: int = 20):
    try:
        r = requests.post(url, json=body, headers=headers or {}, timeout=timeout)
        return r
    except Exception as e:
        st.error(f"Network error calling {url}: {e}")
        return None


def detect_language(text: str) -> str:
    """
    Return detected language code or 'en' fallback.
    Uses LibreTranslate public instance.
    """
    if not text:
        return "en"
    try:
        r = json_post(f"{LIBRETRANSLATE_BASE}/detect", {"q": text})
        if r is None:
            return "en"
        j = r.json()
        if isinstance(j, list) and len(j) > 0 and "language" in j[0]:
            return j[0]["language"]
    except Exception:
        pass
    return "en"


def translate(text: str, source: str, target: str) -> str:
    """
    Translate using LibreTranslate. Returns translated text or original text on failure.
    """
    if not text:
        return text
    # If requested languages are identical, fast-return
    if source == target:
        return text
    try:
        r = json_post(
            f"{LIBRETRANSLATE_BASE}/translate",
            {"q": text, "source": source or "auto", "target": target, "format": "text"},
        )
        if r is None:
            return text
        j = r.json()
        # LibreTranslate returns {translatedText: "..."}
        if isinstance(j, dict) and "translatedText" in j:
            return j["translatedText"]
        # if it's raw string or other shape
        if isinstance(j, str):
            return j
        # safe fallback
        return str(j)
    except Exception:
        return text


def crisis_check(text_en: str) -> bool:
    if not text_en:
        return False
    low = text_en.lower()
    return any(p in low for p in CRISIS_PATTERNS)


def generate_reply_hf(prompt: str) -> str:
    """
    Call Hugging Face Inference API to generate a response.
    Returns generated text or None on failure.
    """
    if not HF_API_TOKEN:
        # graceful fallback to a safe canned reply if token not provided
        return "I hear you. Thanks for sharing that. Could you tell me one small thing that happened recently that made you feel this way?"
    try:
        headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
        payload = {
            "inputs": prompt,
            "parameters": {"max_new_tokens": 200, "temperature": 0.7},
            "options": {"wait_for_model": True},
        }
        r = requests.post(f"https://api-inference.huggingface.co/models/{HF_MODEL}",
                          headers=headers, json=payload, timeout=60)
        if not r.ok:
            # Surface error for debugging
            st.session_state["_last_hf_error"] = f"HF error {r.status_code}: {r.text[:400]}"
            return None
        data = r.json()
        # common shape: [{ "generated_text": "..." }]
        if isinstance(data, list) and len(data) and "generated_text" in data[0]:
            return data[0]["generated_text"].strip()
        # fallback if data is dict with generated_text
        if isinstance(data, dict) and "generated_text" in data:
            return data["generated_text"].strip()
        # sometimes we get plain text
        if isinstance(data, str):
            return data.strip()
        # last resort: stringify
        return str(data)
    except Exception as e:
        st.session_state["_last_hf_error"] = f"HF network error: {e}"
        return None


def make_system_prompt():
    return (
        "You are MindMitra, a calm and empathetic companion for young people. "
        "Keep replies short and supportive (2-5 sentences). Validate the user's feelings, offer one simple coping tip "
        "(breathing, grounding, short activity, or approach), and gently suggest reaching out to a trusted person or professional if needed. "
        "Do not give medical advice or attempt to diagnose. Use plain friendly language."
    )


# ---------------------------
# Streamlit UI
# ---------------------------
st.set_page_config(page_title="MindMitra", page_icon="💜", layout="centered")

st.markdown("<h1 style='color:#5b21b6'>MindMitra</h1>", unsafe_allow_html=True)
st.markdown("Private, multilingual companion for youth mental wellness. Not a medical service.")

# Initialize session state
if "history" not in st.session_state:
    st.session_state.history = []  # list of dicts: {role:'user'/'bot', 'text':..., 'lang':...}
if "_last_hf_error" not in st.session_state:
    st.session_state["_last_hf_error"] = None

with st.sidebar:
    st.header("Settings")
    reply_lang = st.selectbox(
        "Reply language (choose or keep Auto)",
        options=[
            "Auto",
            "English (en)",
            "Hindi (hi)",
            "Bengali (bn)",
            "Marathi (mr)",
            "Tamil (ta)",
            "Telugu (te)",
            "Gujarati (gu)",
            "Kannada (kn)",
            "Malayalam (ml)",
            "Punjabi (pa)",
            "Odia (or)",
            "Spanish (es)",
        ],
        index=0,
    )
    st.markdown("---")
    st.markdown("**Privacy**: messages are not stored on disk. All conversation history is in your browser session only.")
    st.markdown("**Tip**: For best results, keep messages to a few sentences.")

# Main chat area
col1, col2 = st.columns([3, 1])
with col1:
    st.subheader("Chat")
    chat_box = st.empty()
    # render history
    def render_history():
        html_parts = []
        for m in st.session_state.history:
            who = m.get("role", "bot")
            text = html.escape(m.get("text", ""))
            if who == "user":
                html_parts.append(f"<div style='text-align:right;margin:8px 0;'><div style='display:inline-block;background:#eef2ff;padding:10px;border-radius:12px;max-width:80%'>{text}</div></div>")
            else:
                html_parts.append(f"<div style='text-align:left;margin:8px 0;'><div style='display:inline-block;background:#f8fafc;padding:10px;border-radius:12px;max-width:80%'>{text}</div></div>")
        chat_box.markdown("\n".join(html_parts), unsafe_allow_html=True)
    render_history()

with col2:
    pass  # reserved for future small widgets

# Input area
st.markdown("---")
col_a, col_b = st.columns([4, 1])
with col_a:
    user_input = st.text_area("You (type in any supported language)", key="user_input", placeholder="Type how you feel...")
with col_b:
    send = st.button("Send", type="primary")

if send:
    msg = user_input.strip()
    if not msg:
        st.warning("Please enter a message.")
    else:
        # add to history
        st.session_state.history.append({"role": "user", "text": msg})
        # clear input area
        st.session_state.user_input = ""
        render_history()

        # 1) detect language
        detected_lang = detect_language(msg) or "en"
        # 2) translate to English if necessary
        msg_en = msg
        if detected_lang != "en":
            msg_en = translate(msg, detected_lang, "en")

        # 3) crisis check
        if crisis_check(msg_en):
            reply_en = (
                "I'm really sorry you're feeling this much pain. " +
                "You are not alone. " + CRISIS_HELPLINE
            )
            # Add to history (translated back if needed)
            out_lang_code = "en"
            if reply_lang != "Auto":
                # parse reply_lang like "Hindi (hi)" -> hi
                out_lang = reply_lang.split("(")[-1].strip(")")
                out_lang_code = out_lang
            else:
                out_lang_code = detected_lang or "en"
            reply_out = reply_en
            if out_lang_code != "en":
                reply_out = translate(reply_en, "en", out_lang_code)
            st.session_state.history.append({"role": "bot", "text": reply_out})
            render_history()
        else:
            # 4) compose prompt and call HF
            system_prompt = make_system_prompt()
            prompt = f"{system_prompt}\n\nUser: {msg_en}\n\nAssistant:"
            with st.spinner("Thinking..."):
                reply_en = generate_reply_hf(prompt)
                # if HF returned None, show friendly fallback
                if reply_en is None:
                    reply_en = "I understand. That sounds hard. Can you tell me one small detail about what's happening right now?"
                # 5) determine output language: requested or detected
                if reply_lang != "Auto":
                    out_lang = reply_lang.split("(")[-1].strip(")")
                else:
                    out_lang = detected_lang or "en"
                reply_out = reply_en
                if out_lang != "en":
                    reply_out = translate(reply_en, "en", out_lang)
                # 6) append to history and render
                st.session_state.history.append({"role": "bot", "text": reply_out})
                render_history()

# show hf error if exists
if st.session_state.get("_last_hf_error"):
    st.error("Model/Inference warning: " + st.session_state["_last_hf_error"])

# Footer
st.markdown("---")
st.markdown(
    """
    **Disclaimer:** MindMitra is an AI companion, not a medical or crisis service. If you are in immediate danger, contact local emergency services.
    """
)
