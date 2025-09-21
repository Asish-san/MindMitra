# MindMitra
MindMitra – AI-Powered Mental Wellness Companion

Quick start:
1. Create a GitHub repo and push files.
2. Create a Vercel project from that repo.
3. Add env var HF_API_TOKEN (your Hugging Face token).
4. Deploy and open URL.

API:
POST /api/chat
Body: { "message": "text", "lang": "hi" }
Response: { "reply": "...", "reply_lang": "hi", "detected_lang": "hi", "crisis": false }
