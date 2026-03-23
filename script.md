# Randi Agency — Twilio Call Flow Script

## Main Greeting (played on every inbound call)

> "Hey, thanks for calling Randi Agency. I'm Billy — we help local businesses show up where customers are actually searching in 2026: AI search, Google, and beyond.
>
> Press 1 to get your free AI Visibility Audit — we'll show you exactly where your business stands and what's costing you customers.
>
> Press 2 to schedule a call with me directly.
>
> Or stay on the line and leave a message — I'll get back to you personally."

---

## Press 1 — Free Audit SMS

SMS sent to caller:
> "Hey, it's Billy at Randi Agency! Here's your free AI Visibility Audit link: https://randi.agency/free-audit.html — takes 60 seconds to fill out and we'll have your results back within 24 hours. Talk soon!"

---

## Press 2 — Book a Call SMS

SMS sent to caller:
> "Hey, it's Billy at Randi Agency! Head to https://randi.agency/contact.html to pick a time that works for you. Looking forward to talking! — Billy"

---

## No Input / Voicemail Prompt

> "No worries — leave your name, number, and what you're looking for, and I'll call you back personally. Thanks!"

---

## Flow Logic

```
Inbound call
    → Play greeting
    → Gather digit (timeout: 10s)
        → 1: Send audit SMS → play confirmation → hang up
        → 2: Send booking SMS → play confirmation → hang up
        → timeout/no input: Play voicemail prompt → Record → hang up
```
