# FinePrint — Legal AI Assistant

> A GenAI system that analyzes legal documents (employment offer letters, training bonds) and produces a **Position Report** — a grounded statement of where the user stands.

⚠️ **This tool provides information, not legal advice.** Every output is for educational purposes and should be confirmed with a qualified legal professional.

## Features

- **Obligations Timeline** — What must you do, and by when?
- **Is This Normal?** — Is each clause standard, stricter than usual, or unusual?
- **Enforceability Flags** — Which clauses may not hold up under Indian law?
- **Your Move** — Suggested redlines + a drafted negotiation email
- **Lawyer Prep Brief** — A one-page PDF to take to a professional
- **Grounded Q&A** — Ask questions about your document; the system abstains when unsure

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, SQLite
- **Frontend**: React 18, Vite, TypeScript, Tailwind CSS
- **LLM**: Provider-agnostic (OpenAI-compatible API)
- **OCR**: Tesseract + OpenCV for phone photos

## Quick Start

```bash
# Backend
cd fineprint/backend
pip install -r ../requirements.txt
cp ../.env.example ../.env  # fill in your API keys
uvicorn main:app --reload --port 8000

# Frontend
cd fineprint/frontend
npm install
npm run dev
```

## Environment Variables

```
LLM_MODEL=gpt-4o
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-...
EMBED_MODEL=text-embedding-3-small
MOCK_LLM=0
```

## License

Built for Hack2Skills PromptWars — AI Evolution Module.
