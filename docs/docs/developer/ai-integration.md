# AI Integration

Nexara abstracts AI vendors behind `AIProvider`
(`backend/app/services/ai/provider.py`). AI is optional: if unconfigured,
`create_provider(settings)` returns `None` and callers must degrade gracefully.

## Protocol

All methods are async and return `(result, cost_cents, token_count)`.

| Method | Signature | Result |
|---|---|---|
| `complete` | `(prompt, max_tokens, temperature)` | text |
| `vision` | `(image_bytes, prompt, max_tokens)` | text |
| `embed` | `(text)` | `list[float]` (Anthropic: `NotImplementedError`) |
| `count_tokens` | `(text)` | token count (local ~4 chars/token estimate) |

## Configuration

| Variable | Purpose |
|---|---|
| `AI_PROVIDER` | `anthropic`, `openai` or `ollama` (empty = disabled) |
| `ANTHROPIC_API_KEY` | required for `anthropic` |
| `OPENAI_API_KEY` | required for `openai` |
| `OLLAMA_BASE_URL` | required for `ollama`, e.g. `http://ollama:11434` |
| `OLLAMA_MODEL` | Ollama model, default `llama2` |
| `AI_HTTP_TIMEOUT` | request timeout in seconds (default 60) |

A selected provider with missing variables raises `AIProviderConfigError`.
An empty or unknown `AI_PROVIDER` yields `None`.

## Pricing (USD per 1M tokens, input / output)

| Provider | Use | Model | Rates |
|---|---|---|---|
| Anthropic | text | claude-3-haiku | 0.25 / 1.25 |
| Anthropic | vision | claude-3-sonnet | 3.00 / 15.00 |
| OpenAI | text | gpt-4o-mini | 0.15 / 0.60 |
| OpenAI | vision | gpt-4o | 2.50 / 10.00 |
| OpenAI | embeddings | text-embedding-3-small | 0.02 / - |
| Ollama | any | `OLLAMA_MODEL` | free (cost 0) |

Cost in cents = `(in * in_rate + out * out_rate) / 1e6 * 100`, from the
usage counts the API returns. Rates live in each provider's `PRICING` dict.
