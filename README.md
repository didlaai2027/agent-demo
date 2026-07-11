# Wander — AI Travel Planner

A minimal travel website with a floating **AI travel agent** widget. The widget
runs the same interview as the terminal script [`agent-demo2.py`](./agent-demo2.py)
and streams a full trip plan from Claude — destinations, itinerary, sample
flights, and a budget.

**Live demo:** https://agent-demo-hazel.vercel.app

## Structure

| Path | Purpose |
|------|---------|
| `index.html` | The travel site + floating agent window (static, self-contained). |
| `api/plan.py` | Vercel Python serverless function. Same model & system prompt as the terminal agent; streams the plan back to the browser. |
| `agent-demo2.py` | The original terminal agent (unchanged). |
| `requirements.txt` | Python deps for the serverless function (`anthropic`). |
| `vercel.json` | Static-site + Python function config (60s max duration for streaming). |

## Configuration

The Anthropic API key is **not** committed. Set it as an environment variable
in the Vercel project:

```
ANTHROPIC_API_KEY=sk-ant-...
```

Locally, the terminal agent reads it from `config.env` (gitignored).

## Local dev

```bash
npx vercel dev
```

## Deploy

```bash
npx vercel --prod
```
