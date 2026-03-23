"""
Run this after deploying to Railway to point your Twilio number at the new URL.
Usage: python3 update_twilio_webhook.py
"""
import os
from twilio.rest import Client

account_sid = os.environ.get('TWILIO_ACCOUNT_SID', 'AC722795bf926f33c1e6cd3fc1d007fd16')
auth_token  = os.environ.get('TWILIO_AUTH_TOKEN',  'b54d88510f92a6bfeea629585ac11e2a')
twilio_number = os.environ.get('TWILIO_NUMBER', '+14788272634')
base_url = os.environ.get('BASE_URL', '')

if not base_url:
    base_url = input("Enter your Railway public URL (e.g. https://twilio-callflow.up.railway.app): ").strip()

webhook_url = f"{base_url}/voice"
client = Client(account_sid, auth_token)

numbers = client.incoming_phone_numbers.list()
for num in numbers:
    if num.phone_number == twilio_number:
        updated = client.incoming_phone_numbers(num.sid).update(
            voice_url=webhook_url,
            voice_method='POST'
        )
        print(f"✅ Twilio number {twilio_number} now points to: {updated.voice_url}")
        break
else:
    print(f"❌ Number {twilio_number} not found in your Twilio account.")
