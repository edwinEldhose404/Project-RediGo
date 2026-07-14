# RediGo API

Start a local MongoDB instance, install [Ollama](https://ollama.com/), and download the
default local summarization model:

```powershell
ollama pull gemma3:4b
pip install -r requirements.txt
uvicorn src.api:app --reload --port 8000
```

Keep Ollama running while the API is in use. The frontend at `http://localhost:4200`
calls this API automatically. The root `.env` only needs the Reddit credentials
expected by `reddit_summarizer.py`; `GOOGLE_AI_KEY` is no longer used.

To use a different local model, set `OLLAMA_MODEL` in `.env`, for example
`OLLAMA_MODEL=qwen3:4b`.
