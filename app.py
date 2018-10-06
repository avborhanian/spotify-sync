from base64 import b64encode
from datetime import datetime, timedelta
import os

from flask import Flask, request, render_template, jsonify
from flask_socketio import SocketIO, join_room, disconnect, emit
import requests

from db import session_scope, init_db

app = Flask(__name__)

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")


def get_access_token():
    with session_scope() as session:
        result = session.execute("""
            select access_token, expires_on from token
        """).fetchall()
        if not result or result[1] < datetime.now():
            combined_clients = ":".join((SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET))
            basic_auth = f'Basic {b64encode(combined_clients.encode()).decode()}'
            resp = requests.post("https://accounts.spotify.com/api/token",
                                  headers={'authorization': basic_auth},
                                  data={'grant_type': 'client_credentials'})
            if resp.status_code == 200:
                info = resp.json()
                expire_dt = datetime.now() + timedelta(seconds=int(info["expires_in"]))
                session.execute("""
                update token 
                set access_token = :token,
                expires_on = :time""", dict(token=info['access_token'],
                                            time=expire_dt))
                return info['access_token']
            else:
                raise Exception(f"Error contacting Spotify, {resp.reason()}")
        else:
            return result[0]



@app.route("/")
def index():
    return render_template("index.html")


@app.route("/room")
def room():
    return render_template("room.html")


@app.route("/api/search")
def search():
    token = f"Bearer {get_access_token()}"
    search_text = request.args.get("q", "")
    if not search_text.strip():
        response = {'data': []}
    else:
        return jsonify(requests.get("https://api.spotify.com/v1/search",
                                    headers={"authorization": token},
                                    params={"q": search_text,
                                            "type": "track",
                                            "limit": 50}).json())

if __name__ == '__main__':
    init_db()
    app.run(host="0.0.0.0", debug=True, port=5000)
