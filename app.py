import streamlit as st
from googletrans import Translator
from transformers import pipeline
import random

# -----------------------------
# Setup
# -----------------------------
st.set_page_config(page_title="MindMitra", page_icon="💜", layout="centered")
st.title("💜 MindMitra — your private, multilingual wellness buddy")

if "history" not in st.session_state:
    st.session_state.history = []

# Translator
translator = Translator()

# Hugging Face pipelines
sentiment_analyzer = pipeline("sentiment-analysis")
generator = pipeline("text-generation", model="gpt2")

# -----------------------------
# Core function
# -----------------------------
def get_supportive_reply(user_text: str, lang: str = "en") -> str:
    # Detect language
    detected = translator.detect(user_text).lang
    translated = translator.translate(user_text, dest="en").text

    # Sentiment
    sentiment = sentiment_analyzer(translated)[0]
    label, score = sentiment["label"], sentiment["score"]

    # Generate empathetic response
    base_prompt = f"The user feels: {translated}. They are {label.lower()} (confidence {score:.2f}). "
    base_prompt += "Reply kindly, like a caring friend, short and simple."

    response = generator(base_prompt, max_length=80, num_return_sequences=1)
    english_reply = response[0]["generated_text"].split("Reply kindly")[-1].strip()

    # Translate back to original language if not English
    if detected != "en":
        final_reply = translator.translate(english_reply, dest=detected).text
    else:
        final_reply = english_reply

    return final_reply

# -----------------------------
# Chat UI
# -----------------------------
st.markdown("### Talk to me 👇")
col_a, col_b = st.columns([4, 1])

with col_a:
    user_input = st.text_area(
        "You (type in any supported language)",
        key="user_input",
        placeholder="Type how you feel..."
    )
with col_b:
    send = st.button("Send", type="primary")

if send:
    msg = st.session_state.user_input.strip()
    if msg:
        # Save user message
        st.session_state.history.append({"role": "user", "text": msg})

        # Generate reply
        reply = get_supportive_reply(msg)
        st.session_state.history.append({"role": "bot", "text": reply})

        # Clear input safely
        st.session_state.user_input = ""
        st.experimental_rerun()

# -----------------------------
# Display chat
# -----------------------------
for chat in st.session_state.history:
    if chat["role"] == "user":
        st.markdown(f"🧑 **You:** {chat['text']}")
    else:
        st.markdown(f"🤖 **MindMitra:** {chat['text']}")

st.markdown("---")
st.caption("⚠️ Disclaimer: This is a supportive AI buddy, **not a medical professional**. If you feel overwhelmed, please reach out to a trusted person or counselor.")
