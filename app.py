import streamlit as st
import requests
from deep_translator import GoogleTranslator

# ---------------------------
# CONFIG
# ---------------------------
st.set_page_config(page_title="MindMitra", page_icon="🧘", layout="wide")

HF_API_URL = "https://api-inference.huggingface.co/models/google/flan-t5-base"
HF_API_KEY = st.secrets.get("HF_API_KEY", None)  # store in Streamlit Cloud secrets

headers = {"Authorization": f"Bearer {HF_API_KEY}"} if HF_API_KEY else {}

# ---------------------------
# SESSION STATE
# ---------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

# ---------------------------
# APP TITLE
# ---------------------------
st.title("🧘 MindMitra - AI Wellness Companion")
st.write("Your multilingual emotional support chatbot, powered by **AI & free translation**.")

# ---------------------------
# SIDEBAR
# ---------------------------
st.sidebar.header("⚙️ Settings")
language = st.sidebar.selectbox(
    "Choose language for replies:",
    ["english", "hindi", "odia", "bengali", "spanish", "french"],
)
st.sidebar.info("Using Hugging Face free LLM + Deep Translator")

# ---------------------------
# AI REPLY FUNCTION
# ---------------------------
def get_ai_reply(prompt: str) -> str:
    """Fetch AI response from HuggingFace model."""
    if not HF_API_KEY:
        return "⚠️ HuggingFace API Key missing. Please add it in Streamlit secrets."

    payload = {"inputs": f"You are a kind and supportive friend. Reply briefly: {prompt}"}
    try:
        response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()

        if isinstance(data, list) and "generated_text" in data[0]:
            reply = data[0]["generated_text"]
        else:
            reply = "I'm here for you. Please share more."

    except Exception as e:
        reply = f"⚠️ AI error: {e}"

    # Translate if not English
    if language.lower() != "english":
        try:
            reply = GoogleTranslator(source="english", target=language).translate(reply)
        except Exception:
            reply = reply + "\n\n(⚠️ Translation failed.)"

    return reply

# ---------------------------
# CHAT INPUT
# ---------------------------
user_input = st.text_input("💬 Share your thoughts:", key="chat_input")

if st.button("Send"):
    if user_input.strip():
        st.session_state.messages.append({"role": "user", "content": user_input})
        reply = get_ai_reply(user_input)
        st.session_state.messages.append({"role": "ai", "content": reply})
    else:
        st.warning("Please type a message before sending.")

# ---------------------------
# DISPLAY CHAT
# ---------------------------
st.subheader("🗨️ Conversation")
if not st.session_state.messages:
    st.info("Start by typing your first thought above.")
else:
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f"👤 **You:** {msg['content']}")
        else:
            st.markdown(f"🤖 **MindMitra:** {msg['content']}")

# ---------------------------
# FOOTER
# ---------------------------
st.markdown("---")
st.caption("© 2025 MindMitra | Free AI wellness support app")
