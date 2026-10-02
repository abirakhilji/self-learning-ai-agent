# Self-Learning AI Agent

A small Python agent that **improves from experience**. After each task it reflects on what happened, stores a short lesson in a SQLite memory, and retrieves relevant lessons before the next task.

The model's weights are never changed. The agent gets better because its memory gets better.

Runs on **Google's Gemini API free tier** — no credit card needed.

## How it works

```
task -> retrieve lessons -> act (model + tools) -> answer
                                                     |
                     store lesson <- reflect <- feedback (optional)
```

| File | Purpose |
|------|---------|
| `agent.py` | Tool-use loop, reflection, interactive CLI |
| `memory.py` | SQLite lesson store with keyword retrieval |
| `tools.py` | Calculator, sandboxed file tools, clock |
| `evaluate.py` | Measures the agent with and without memory |

## Setup

1. Get a free API key from **Google AI Studio** (aistudio.google.com → "Get API key" → "Create API key"). No credit card required for the free tier.
2. Install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate        # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Set up your key:
   ```bash
   cp .env.example .env            # Windows: copy .env.example .env
   ```
   Open `.env` and paste your key after `GEMINI_API_KEY=`.

## Run

```bash
python agent.py       # chat; give feedback after each answer so it can learn
python evaluate.py    # baseline vs. with-memory comparison
```

CLI commands: `/lessons` shows what it has learned, `/forget` clears memory, `/quit` exits.

## The evaluation

`evaluate.py` sets a hidden rule (answers must be only a bare number). The tasks never state it. The agent fails at first, receives feedback, stores a lesson, and is then re-tested on similar tasks. Compare the scores from Phase A (no memory) and Phase C (with memory).

## Notes on the free tier

- The default model is `gemini-3.8-flash`. If Google renames or retires it, check aistudio.google.com for the current free-tier model name and set `AGENT_MODEL` in `.env`.
- The free tier has a daily request limit. `evaluate.py` makes under 20 calls, well within it.

## Ideas to extend

- Replace keyword retrieval with embeddings for better lesson matching
- Add more tools (web search, code execution in a sandbox)
- Let the agent merge or rewrite old lessons so memory stays small
- Add a Streamlit interface

## License

MIT
