# LMGate

Monitor, control, and govern LLM API usage at scale.

## What is LMGate?

LMGate is a gateway that sits between your applications and LLM API providers. It acts as a pass-through proxy that controls access to every LLM API's and tracks usage — without changing how your applications connect to LLM services.

## When Do You Need LMGate?

- You need a single place to see total LLM API spend across teams and projects.
- You want rate limits or access policies on outbound LLM API calls.
- You need an audit log of who called what model, when, and how many tokens it consumed.
- You want to attribute API costs to specific teams, services, or projects.
- You need to enforce usage policies without touching every application's code.

## Core Capabilities

- **Access control** — Define who can access which models, set rate limits, and enforce approval policies.
- **Usage monitoring** — Track token consumption, request volume, latency, and costs per team, project, or API key in real time.
- **Budget governance** — Set spend limits and alerts at the org, team, or project level.
- **Audit logging** — Maintain a complete record of all LLM API interactions for compliance and debugging.
- **Provider-agnostic** — Works with OpenAI, Anthropic, Google, and other LLM API providers.

## How It Works
```
Your Apps → LMGate (proxy) → LLM Provider APIs
```

LMGate operates as a lightweight reverse proxy. Point your applications to LMGate instead of directly to the provider endpoint. LMGate forwards requests transparently while capturing metadata, enforcing policies, and logging activity.


## Getting Started
```bash
git clone git@github.com:numio-ai/lmgate.git
cd lmgate
```

> 🚧 LMGate is in early development. Setup and usage docs are coming soon.

## License

Apache 2.0 — see [LICENSE](LICENSE) for details.