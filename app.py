import streamlit as st
from deep_translator import GoogleTranslator

# ---------------------------
# Page Config
# ---------------------------
st.set_page_config(page_title="MindMitra", page_icon="🧘", layout="wide")

# ---------------------------
# Initialize session state
# ---------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "user_input" not in st.session_state:
    st.session_state.user_input = ""

# ---------------------------
# App Title
# ---------------------------
st.title("🧘 MindMitra - Your Free AI Wellness Companion")

st.write(
    "Welcome to **MindMitra**, a free AI-powered mental wellness companion. "
    "Chat, translate your thoughts, and get supportive responses instantly."
)

# ---------------------------
# Sidebar
# ---------------------------
st.sidebar.header("⚙️ Settings")

language = st.sidebar.selectbox(
    "Choose language for replies:",
    ["english", "hindi", "odia", "bengali", "spanish", "french"],
)

st.sidebar.markdown("---")
st.sidebar.write("Built with ❤️ using Streamlit and Deep-Translator.")

# ---------------------------
# Core Chatbot Function
# ---------------------------
def get_ai_reply(prompt: str) -> str:
    """
    Dummy AI reply generator.
    You can expand this later with any open-source LLM API (like HuggingFace).
    """
    base_reply = (
        "I hear you. It's normal to feel this way sometimes. "
        "Remember to breathe deeply and be kind to yourself."
    )

    # Translate if not English
    if language.lower() != "english":
        try:
            translated = GoogleTranslator(source="english", target=language).translate(base_reply)
            return translated
        except Exception:
            return "⚠️ Translation failed. Showing English response:\n\n" + base_reply
    return base_reply

# ---------------------------
# Chat Input
# ---------------------------
user_input = st.text_input("💬 Share your thoughts:", key="chat_input")

if st.button("Send"):
    if user_input.strip():
        st.session_state.messages.append({"role": "user", "content": user_input})

        reply = get_ai_reply(user_input)
        st.session_state.messages.append({"role": "ai", "content": reply})

        st.session_state.user_input = ""
    else:
        st.warning("Please type a message before sending.")

# ---------------------------
# Display Chat
# ---------------------------
st.subheader("🗨️ Conversation")

if len(st.session_state.messages) == 0:
    st.info("Start the conversation by typing your first thought above.")
else:
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f"👤 **You:** {msg['content']}")
        else:
            st.markdown(f"🤖 **MindMitra:** {msg['content']}")

# ---------------------------
# Footer
# ---------------------------
st.markdown("---")
st.caption("© 2025 MindMitra | Free AI wellness support app")
