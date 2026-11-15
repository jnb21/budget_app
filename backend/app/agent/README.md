# agent/

All the agentic (AI) work of the app lives here: the LLM loop, the tools the
model can call, and the prompts.

## The rule

The agent reaches data **only through services**, never through repositories
or the database:

```
/agent router → agent loop → tools → services → repositories → Postgres
                                         ↑
                          the same services the UI uses
```

So the agent follows the same business rules and the same per-user
filtering (`user_id`) as a click in the app. A prompt-injected model can only
do what a service allows for that user.

`tests/test_architecture.py` enforces this: it fails if any file here imports
`app.repositories`, `app.db`, `psycopg` or `psycopg_pool`.

## Planned files (not written yet)

| File | Job |
|---|---|
| `llm.py` | Talks to the LLM API (the only file that knows the provider) |
| `tools.py` | The functions the model may call; each one calls a service |
| `loop.py` | Sends the conversation, runs the tools the model asks for, repeats until it answers |
| `prompts.py` | The system prompt and tool descriptions |

## Open question

What is the agent for? (chat questions about spending, budget suggestions,
or auto-categorizing transactions). The answer decides the first tools.
