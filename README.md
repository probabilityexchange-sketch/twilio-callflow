# Randi Agency — Twilio Call Flow

Flask webhook server that powers the inbound call flow for **(478) 827-RANDI**.

## Call Flow

```
Inbound call → Greeting (Randi voice)
  → Press 1 → SMS with free audit link → confirmation
  → Press 2 → SMS with booking link → confirmation
  → No input → Voicemail prompt → Record → Transcribe → Log to Sheets
```

## Environment Variables

| Variable | Description |
|---|---|
| `TWILIO_ACCOUNT_SID` | Twilio Account SID |
| `TWILIO_AUTH_TOKEN` | Twilio Auth Token |
| `TWILIO_NUMBER` | Your Twilio number e.g. `+14788272634` |
| `SHEETS_ID` | Google Sheets ID for call log |
| `BASE_URL` | Public URL of this server (no trailing slash) |
| `PORT` | Port to run on (default: 5050) |

## Deploy to Railway

1. Connect this repo in Railway
2. Set all environment variables above
3. Railway auto-detects Python/Flask — no config needed
4. Copy the Railway URL and update `BASE_URL`
5. Run `python update_twilio_webhook.py` to point Twilio at the new URL

## Audio Files

All audio is in `/audio/` — regenerate any clip by running:
```bash
# Edit the text in generate_audio.py then run:
python3 generate_audio.py
```

## Local Development

```bash
pip install -r requirements.txt
BASE_URL=http://localhost:5050 python3 app.py
```
