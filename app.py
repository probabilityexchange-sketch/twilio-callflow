import os
import smtplib
from email.mime.text import MIMEText
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

# Email config for voicemail transcripts
SMTP_HOST     = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT     = int(os.environ.get('SMTP_PORT', '587'))
SMTP_USER     = os.environ.get('SMTP_USER', '')       # Gmail address used to send
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')   # Gmail app password

AGENCY_EMAIL    = 'billy@randi.agency'
INDUSTRIES_EMAIL = 'billy@randi.industries'

AUDIT_URL   = 'https://randi.agency/free-audit.html'
CONTACT_URL = 'https://randi.agency/contact.html'

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# --- Helpers ---

def audio_url(filename):
    return f"{BASE_URL}/audio/{filename}"

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

def send_email(to_addr, subject, body):
    """Send a plain-text email via SMTP. Silently skips if SMTP creds not set."""
    if not SMTP_USER or not SMTP_PASSWORD:
        print(f"Email skipped (no SMTP creds): {subject}")
        return
    try:
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = SMTP_USER
        msg['To'] = to_addr
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, [to_addr], msg.as_string())
        print(f"Email sent to {to_addr}: {subject}")
    except Exception as e:
        print(f"Email error: {e}")

# --- Routes ---

@app.route('/health')
def health():
    """Health check endpoint for monitoring."""
    return {'status': 'ok', 'service': 'randi-twilio-callflow', 'number': TWILIO_NUMBER}, 200

@app.route('/gather', methods=['GET', 'POST'])
def gather_alias():
    """Alias for /voice/handle-key — used by health checks."""
    return handle_key()

@app.route('/audio/<filename>')
def serve_audio(filename):
    return send_from_directory(os.path.join(os.path.dirname(__file__), 'audio'), filename)


# ============================================================
# TOP-LEVEL ROUTING MENU
# Press 1 → Randi Agency
# Press 2 → Randi Industries
# No input → general voicemail
# ============================================================

@app.route('/voice', methods=['GET', 'POST'])
def voice():
    """Main inbound call handler — play routing greeting and gather digit."""
    response = VoiceResponse()
    gather = Gather(num_digits=1, action='/voice/route', timeout=10)
    gather.play(audio_url('routing-greeting.wav'))
    response.append(gather)
    # No input — go to general voicemail
    response.redirect('/voice/voicemail')
    return Response(str(response), mimetype='text/xml')

@app.route('/voice/route', methods=['GET', 'POST'])
def route():
    """Route caller based on top-level digit press."""
    digit = request.form.get('Digits', '')
    caller = request.form.get('From', 'Unknown')
    response = VoiceResponse()

    if digit == '1':
        log_to_sheets(caller, 'Routed to Randi Agency')
        response.redirect('/voice/agency')
    elif digit == '2':
        log_to_sheets(caller, 'Routed to Randi Industries')
        response.redirect('/voice/industries')
    else:
        response.redirect('/voice/voicemail')

    return Response(str(response), mimetype='text/xml')


# ============================================================
# RANDI AGENCY FLOW  (Press 1 at top menu)
# Press 1 → Free Audit SMS
# Press 2 → Book a Call SMS
# No input → general voicemail
# ============================================================

@app.route('/voice/agency', methods=['GET', 'POST'])
def agency():
    """Randi Agency sub-menu — play greeting and gather digit."""
    response = VoiceResponse()
    gather = Gather(num_digits=1, action='/voice/agency/handle-key', timeout=10)
    gather.play(audio_url('greeting.wav'))
    response.append(gather)
    response.redirect('/voice/voicemail')
    return Response(str(response), mimetype='text/xml')

@app.route('/voice/agency/handle-key', methods=['GET', 'POST'])
def agency_handle_key():
    """Handle digit press inside Randi Agency flow."""
    digit = request.form.get('Digits', '')
    caller = request.form.get('From', 'Unknown')
    response = VoiceResponse()

    if digit == '1':
        try:
            client.messages.create(
                body=f"Hey, it's Billy at Randi Agency! Here's your free AI Visibility Audit link: {AUDIT_URL} — takes 60 seconds to fill out and we'll have your results back within 24 hours. Talk soon!",
                from_=TWILIO_NUMBER,
                to=caller
            )
            log_to_sheets(caller, 'Agency — Pressed 1 — Audit SMS sent')
        except Exception as e:
            print(f"SMS error: {e}")
        response.play(audio_url('confirm-audit.wav'))
        response.hangup()

    elif digit == '2':
        try:
            client.messages.create(
                body=f"Hey, it's Billy at Randi Agency! Head to {CONTACT_URL} to pick a time that works for you. Looking forward to talking! — Billy",
                from_=TWILIO_NUMBER,
                to=caller
            )
            log_to_sheets(caller, 'Agency — Pressed 2 — Booking SMS sent')
        except Exception as e:
            print(f"SMS error: {e}")
        response.play(audio_url('confirm-booking.wav'))
        response.hangup()

    else:
        response.redirect('/voice/voicemail')

    return Response(str(response), mimetype='text/xml')


# ============================================================
# RANDI INDUSTRIES FLOW  (Press 2 at top menu)
# Plays voicemail prompt → records message → emails transcript
# to billy@randi.industries
# ============================================================

@app.route('/voice/industries', methods=['GET', 'POST'])
def industries():
    """Randi Industries voicemail — play prompt and record."""
    caller = request.form.get('From', 'Unknown')
    response = VoiceResponse()
    response.play(audio_url('industries-voicemail.wav'))
    response.record(
        max_length=120,
        action='/voice/industries/voicemail-done',
        transcribe=True,
        transcribe_callback='/voice/industries/transcription'
    )
    log_to_sheets(caller, 'Industries — went to voicemail')
    return Response(str(response), mimetype='text/xml')

@app.route('/voice/industries/voicemail-done', methods=['GET', 'POST'])
def industries_voicemail_done():
    """After Industries recording ends."""
    response = VoiceResponse()
    response.hangup()
    return Response(str(response), mimetype='text/xml')

@app.route('/voice/industries/transcription', methods=['GET', 'POST'])
def industries_transcription():
    """Receive Industries voicemail transcription, log to Sheets, and email Billy."""
    caller      = request.form.get('From', 'Unknown')
    transcript  = request.form.get('TranscriptionText', '(no transcript)')
    recording_url = request.form.get('RecordingUrl', '')
    timestamp   = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')

    log_to_sheets(caller, 'Industries — voicemail transcription',
                  f"{transcript} | Recording: {recording_url}")

    subject = f"📞 Randi Industries Voicemail from {caller}"
    body = (
        f"New voicemail for Randi Industries\n"
        f"{'='*40}\n"
        f"From:      {caller}\n"
        f"Time:      {timestamp}\n\n"
        f"Transcript:\n{transcript}\n\n"
        f"Recording: {recording_url}\n"
    )
    send_email(INDUSTRIES_EMAIL, subject, body)

    return Response('', status=204)


# ============================================================
# GENERAL VOICEMAIL  (no input at top menu)
# ============================================================

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
    log_to_sheets(caller, 'General voicemail')
    return Response(str(response), mimetype='text/xml')

@app.route('/voice/voicemail-done', methods=['GET', 'POST'])
def voicemail_done():
    """After general recording ends."""
    response = VoiceResponse()
    response.hangup()
    return Response(str(response), mimetype='text/xml')

@app.route('/voice/transcription', methods=['GET', 'POST'])
def transcription():
    """Receive general voicemail transcription, log to Sheets, and email Billy."""
    caller        = request.form.get('From', 'Unknown')
    transcript    = request.form.get('TranscriptionText', '(no transcript)')
    recording_url = request.form.get('RecordingUrl', '')
    timestamp     = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')

    log_to_sheets(caller, 'General voicemail transcription',
                  f"{transcript} | Recording: {recording_url}")

    subject = f"📞 Randi Agency Voicemail from {caller}"
    body = (
        f"New voicemail for Randi Agency\n"
        f"{'='*40}\n"
        f"From:      {caller}\n"
        f"Time:      {timestamp}\n\n"
        f"Transcript:\n{transcript}\n\n"
        f"Recording: {recording_url}\n"
    )
    send_email(AGENCY_EMAIL, subject, body)

    return Response('', status=204)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5050))
    app.run(host='0.0.0.0', port=port, debug=False)
