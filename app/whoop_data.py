from flask import Flask, request, redirect, session, url_for
from requests_oauthlib import OAuth2Session
import os
import requests
import json

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY')  # Set in env for security

# WHOOP Credentials (store securely in env vars)
CLIENT_ID = os.environ.get('WHOOP_CLIENT_ID')
CLIENT_SECRET = os.environ.get('WHOOP_CLIENT_SECRET')
AUTH_URL = 'https://api.prod.whoop.com/oauth/oauth2/auth'
TOKEN_URL = 'https://api.prod.whoop.com/oauth/oauth2/token'
REDIRECT_URI = 'http://localhost:5000/whoop/connect'  # Register in WHOOP Dashboard
SCOPES = 'offline READ_WORKOUT READ_RECOVERY READ_CYCLES READ_SLEEP READ_BODY_MEASUREMENT READ_PROFILE'

# Helper to get OAuth session
def get_oauth():
    return OAuth2Session(CLIENT_ID, redirect_uri=REDIRECT_URI, scope=SCOPES)

@app.route('/whoop/connect')
def whoop_connect():
    oauth = get_oauth()
    authorization_url, state = oauth.authorization_url(AUTH_URL)
    session['oauth_state'] = state  # CSRF protection
    return redirect(authorization_url)  # User sees privacy policy

@app.route('/whoop/callback')
def whoop_callback():
    oauth = get_oauth()
    if 'oauth_state' not in session or request.args.get('state') != session['oauth_state']:
        return 'CSRF error', 403
    token = oauth.fetch_token(TOKEN_URL, client_secret=CLIENT_SECRET, authorization_response=request.url)
    session['whoop_token'] = token  # Store access/refresh tokens
    return redirect(url_for('ingest_whoop_data'))

@app.route('/whoop/refresh')
def refresh_token():
    token = session.get('whoop_token')
    if not token:
        return 'No token', 400
    oauth = get_oauth()
    new_token = oauth.refresh_token(TOKEN_URL, refresh_token=token['refresh_token'],
                                    client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
    session['whoop_token'] = new_token
    return 'Token refreshed'

@app.route('/whoop/ingest')
def ingest_whoop_data():
    token = session.get('whoop_token')
    if not token:
        return 'Unauthorized', 401
    headers = {'Authorization': f'Bearer {token["access_token"]}'}
    
    # Fetch data using v2 endpoints
    workouts = requests.get('https://api.prod.whoop.com/v2/activity/workout', headers=headers).json()
    recovery = requests.get('https://api.prod.whoop.com/v2/recovery', headers=headers).json()
    cycles = requests.get('https://api.prod.whoop.com/v2/cycle', headers=headers).json()
    sleep = requests.get('https://api.prod.whoop.com/v2/activity/sleep', headers=headers).json()
    body_measurement = requests.get('https://api.prod.whoop.com/v2/user/body_measurement', headers=headers).json()
    profile = requests.get('https://api.prod.whoop.com/v2/user/profile', headers=headers).json()
    
    # Map to your inputs
    ingested_data = {
        'heart_rate_logs': [r.get('resting_heart_rate', 0) for r in recovery.get('recoveries', [])],
        'exercise_history': [{'type': w.get('sport_name', ''), 'duration': w.get('duration', 0),
                             'calories_estimated': w.get('strain_score', 0) * 20} for w in workouts.get('workouts', [])],
        'sleep': [{'duration': s.get('duration', 0), 'quality': s.get('quality_score', 0)} for s in sleep.get('sleeps', [])],
        'body': {'weight': body_measurement.get('weight', 0), 'height': body_measurement.get('height', 0)},
        'user_id': profile.get('user_id', '')  # UUID in v2
    }
    
    # Save for model/RAG (e.g., transformer input)
    with open('whoop_ingested.json', 'w') as f:
        json.dump(ingested_data, f)
    
    return 'Data ingested successfully'

@app.route('/whoop/revoke')
def revoke_token():
    token = session.get('whoop_token')
    if not token:
        return 'No token', 400
    response = requests.post('https://api.prod.whoop.com/developer/v1/user/revoke', 
                            json={'access_token': token['access_token']})
    session.pop('whoop_token', None)
    return 'Access revoked' if response.status_code == 200 else 'Error revoking'

if __name__ == '__main__':
    app.run(debug=True)