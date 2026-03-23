import os
from flask import Flask, request, Response, send_from_directory
from twilio.twiml.voice_response import VoiceResponse, Gather, Play, Record, Say
from twilio.rest import Client
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

app = Flask(__name__)

# --- Config ---
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', 'AC722795bf926f33c1e6cd3fc1d007fd16')
TWILIO_AUTH_TOKEN  = os.environ.get('TWILIO_AUTH_TOKEN',  'b54d88510f92a6bfeea629585ac11e2a')
TWILIO_NUMBER      = os.environ.get('TWILIO_NUMBER',      '+14788272634')
SHEETS_ID          = os.environ.get('SHEETS_ID',          '19hCNdwhOmqdgp1tqZl1AMyBmRL7ne3ZlsEoMKELz4A4')
BASE_URL           = os.environ.get('BASE_URL', '')  # Set to public URL after deploy

AUDIT_URL   = 'https://randi.agency/free-audit.html'
CONTACT_URL = 'https://randi.agency/contact.html'

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# --- Audio files ---
def audio_url(filename):
    return f"{BASE_URL}/audio/{filename}"

# --- Google Sheets helper ---
def log_to_sheets(caller, action, notes=''):
    try:
        scopes = ['https://www.googleapis.com/auth/spreadsheets']
        creds_path = os.path.join(os.path.dirname(__file__), 'service-account.json')
        if not os.path.exists(creds_path):
            return
        creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(SHEETS_ID)
        try:
            ws = sh.worksheet('Call Log')
        except:
            ws = sh.add_worksheet(title='Call Log', rows=1000, cols=10)
            ws.append_row(['Timestamp', 'Caller', 'Action', 'Notes'], value_input_option='RAW')
        ws.append_row([
            datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
            caller,
            action,
            notes
        ], value_input_option='RAW')
    except Exception as e:
        print(f"Sheets log error: {e}")

# --- Routes ---

@app.route('/audio/<filename>')
def serve_audio(filename):
    return send_from_directory(os.path.join(os.path.dirname(__file__), 'audio'), filename)

@app.route('/voice', methods=['GET', 'POST'])
def voice():
    """Main inbound call handler — play greeting and gather digit."""
    response = VoiceResponse()
    gather = Gather(num_digits=1, action='/voice/handle-key', timeout=10)
    gather.play(audio_url('greeting.wav'))
    response.append(gather)
    # No input — go to voicemail
    response.redirect('/voice/voicemail')
    return Response(str(response), mimetype='text/xml')

@app.route('/voice/handle-key', methods=['GET', 'POST'])
def handle_key():
    """Handle digit press."""
    digit = request.form.get('Digits', '')
    caller = request.form.get('From', 'Unknown')
    response = VoiceResponse()

    if digit == '1':
        # Send audit SMS
        try:
            client.messages.create(
                body=f"Hey, it's Billy at Randi Agency! Here's your free AI Visibility Audit link: {AUDIT_URL} — takes 60 seconds to fill out and we'll have your results back within 24 hours. Talk soon!",
                from_=TWILIO_NUMBER,
                to=caller
            )
            log_to_sheets(caller, 'Pressed 1 — Audit SMS sent')
        except Exception as e:
            print(f"SMS error: {e}")
        response.play(audio_url('confirm-audit.wav'))
        response.hangup()

    elif digit == '2':
        # Send booking SMS
        try:
            client.messages.create(
                body=f"Hey, it's Billy at Randi Agency! Head to {CONTACT_URL} to pick a time that works for you. Looking forward to talking! — Billy",
                from_=TWILIO_NUMBER,
                to=caller
            )
            log_to_sheets(caller, 'Pressed 2 — Booking SMS sent')
        except Exception as e:
            print(f"SMS error: {e}")
        response.play(audio_url('confirm-booking.wav'))
        response.hangup()

    else:
        # Unexpected digit — go to voicemail
        response.redirect('/voice/voicemail')

    return Response(str(response), mimetype='text/xml')

@app.route('/voice/voicemail', methods=['GET', 'POST'])
def voicemail():
    """Play voicemail prompt and record message."""
    caller = request.form.get('From', 'Unknown')
    response = VoiceResponse()
    response.play(audio_url('voicemail-prompt.wav'))
    response.record(
        max_length=120,
        action='/voice/voicemail-done',
        transcribe=True,
        transcribe_callback='/voice/transcription'
    )
    log_to_sheets(caller, 'Went to voicemail')
    return Response(str(response), mimetype='text/xml')

@app.route('/voice/voicemail-done', methods=['GET', 'POST'])
def voicemail_done():
    """After recording ends."""
    response = VoiceResponse()
    response.hangup()
    return Response(str(response), mimetype='text/xml')

@app.route('/voice/transcription', methods=['GET', 'POST'])
def transcription():
    """Receive voicemail transcription and log to Sheets."""
    caller = request.form.get('From', 'Unknown')
    transcript = request.form.get('TranscriptionText', '')
    recording_url = request.form.get('RecordingUrl', '')
    log_to_sheets(caller, 'Voicemail transcription', f"{transcript} | Recording: {recording_url}")
    return Response('', status=204)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5050))
    app.run(host='0.0.0.0', port=port, debug=False)
