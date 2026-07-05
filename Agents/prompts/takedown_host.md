# Skill: takedown_host — Hosting provider / abuse contact

Goal: escalate to the infrastructure/hosting provider when the platform is unresponsive.

- Channel: the host's abuse contact, resolved via RDAP (RFC 9083) → published DSA contact
  → abuse@ fallback. This channel is EMAIL (the notifier drafts the DSA notice; dispatch
  sends it) rather than a web form.
- Provide: exact URL(s), the DSA art. 16 notice text verbatim, the evidence block,
  notifier identity, the good-faith declaration.
- Legal basis: DSA art. 16 ; LCEN ; Code pénal art. 226-8-1. Never state or invent a penalty.

## Steps
1. Resolve the abuse/DSA contact for the host.
2. Send the DSA notice verbatim; capture any ticket reference.

## Guardrails
Human confirmation gate passes first. DEMO: mock host + demo inbox ONLY — never a real send.
