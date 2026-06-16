import os
import webbrowser
import threading
from flask import Flask, jsonify
from livekit.api import AccessToken, VideoGrants
from dotenv import load_dotenv

# Load env vars
load_dotenv()

app = Flask(__name__)

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
    return response

@app.route('/api/token')
def get_token():
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    url = os.getenv("LIVEKIT_URL")
    
    if not api_key or not api_secret:
        return jsonify({"error": "Missing LiveKit credentials in .env"}), 500

    token = AccessToken(api_key, api_secret)
    token.with_identity("ui-client")
    token.with_name("Anderson")
    token.with_grants(VideoGrants(room_join=True, room="friday-room"))
    
    return jsonify({
        "token": token.to_jwt(),
        "url": url
    })

if __name__ == '__main__':
    # Start the Flask token API (blocks until killed)
    # NOTE: The browser is opened by the clap detector, not here.
    app.run(port=8001, debug=False, use_reloader=False)
