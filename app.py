import os, requests, gradio as gr

LIBRE = 'https://libretranslate.com'
HF_MODEL = 'google/flan-t5-base'
HF_API = os.environ.get('HF_API_TOKEN', '')

def detect_language(text):
    r = requests.post(f'{LIBRE}/detect', json={'q': text})
    arr = r.json()
    return arr[0]['language'] if arr else 'en'

def translate(text, source, target):
    r = requests.post(f'{LIBRE}/translate', json={'q': text, 'source': source or 'auto', 'target': target, 'format':'text'})
    j = r.json()
    return j.get('translatedText', j)

def hf_generate(prompt):
    if not HF_API:
        return "I hear you. Thanks for sharing that. Can you tell me a bit more?"
    headers = {'Authorization': f'Bearer {HF_API}'}
    payload = {'inputs': prompt, 'parameters': {'max_new_tokens':150, 'temperature':0.7}}
    r = requests.post(f'https://api-inference.huggingface.co/models/{HF_MODEL}', headers=headers, json=payload)
    j = r.json()
    if isinstance(j, list) and j and 'generated_text' in j[0]:
        return j[0]['generated_text']
    if isinstance(j, dict) and 'error' in j:
        return 'Model error: ' + j['error']
    return str(j)

def respond(message, out_lang):
    if not message:
        return "Please type something."
    detected = detect_language(message)
    text_en = translate(message, detected, 'en') if detected != 'en' else message
    # crisis check
    low = text_en.lower()
    crisis_phrases = ['suicide','kill myself','want to die','end my life','hurt myself','self harm']
    if any(p in low for p in crisis_phrases):
        reply_en = "I'm really sorry you are feeling this way. If you are in immediate danger, contact local emergency services. In India, try KIRAN: 1800-599-0019."
    else:
        system = "You are MindMitra, an empathetic, non-judgmental youth support assistant. Keep responses short and practical."
        prompt = f"{system}\n\nUser: {text_en}\n\nAssistant:"
        reply_en = hf_generate(prompt)
    target_lang = out_lang if out_lang else detected
    if target_lang != 'en':
        reply = translate(reply_en, 'en', target_lang)
    else:
        reply = reply_en
    return reply

with gr.Blocks() as demo:
    gr.Markdown("# MindMitra — demo")
    inp = gr.Textbox(lines=4, placeholder="Type what you feel...")
    lang = gr.Dropdown(choices=["","en","hi","es","bn","ta","te","mr","gu","kn","ml","pa","or"], value="")
    out = gr.Textbox(lines=6)
    btn = gr.Button("Send")
    btn.click(fn=respond, inputs=[inp, lang], outputs=[out])

if __name__ == "__main__":
    demo.launch()
