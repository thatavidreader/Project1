import os
import json
import logging
from datetime import date, datetime
from decimal import Decimal

from flask import Flask, request, jsonify, redirect, url_for
from kiteconnect import KiteConnect

logging.basicConfig(level=logging.DEBUG)

PORT = 5010
HOST = "127.0.0.1"
TOKEN_FILE = "access_token.txt"

def serializer(obj):
    return isinstance(obj, (date, datetime, Decimal)) and str(obj)


kite_api_key = "tcic9nehief6209i"
kite_api_secret = "api_secret"

# create a redirect url
redirect_url = f"http://{HOST}:{PORT}/login"

login_url = f"https://kite.zerodha.com/connect/login?api_key={kite_api_key}"

#connect console url
console_url = f"https://developers.kite.trade/apps/{kite_api_key}"

app = Flask(__name__)
app.secret_key = os.urandom(24)

index_template = f"""
    <div>Make sure your app with api_key - <b>{kite_api_key}</b> has set redirect to <b>{redirect_url}</b>.</div>
    <div>If not you can set it from your <a href="{console_url}">Kite Connect developer console here</a>.</div>
    <a href="{login_url}"><h1>Login to generate access token.</h1></a>"""

login_template = """
    <h2 style="color: green">Success</h2>
    <div>Access token: <b>{access_token}</b></div>
    <h4>User login data</h4>
    <pre>{user_data}</pre>
    <a target="_blank" href="/holdings.json"><h4>Fetch user holdings</h4></a>
    <a target="_blank" href="/orders.json"><h4>Fetch user orders</h4></a>
    <a target="_blank" href="https://kite.trade/docs/connect/v1/"><h4>Check Kite Connect docs for other calls.</h4></a>"""

def save_access_token(access_token):
    """Save the access token to a file."""
    with open(TOKEN_FILE, "w") as f:
        f.write(access_token)

def load_access_token():
    """Load the access token from a file."""
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            return f.read().strip()
    return None

def get_kite_client():
    """Return a kite client object"""
    kite = KiteConnect(api_key=kite_api_key)
    access_token = load_access_token()
    if access_token:
        kite.set_access_token(access_token)
    return kite

@app.route("/")
def index():
    access_token = load_access_token()
    if access_token:
        return redirect(url_for('dashboard'))
    else:
        return index_template

@app.route("/login")
def login():
    request_token = request.args.get("request_token")

    if not request_token:
        return """
            <span style="color: red">
                Error while generating request token.
            </span>
            <a href='/'>Try again.</a>"""

    kite = get_kite_client()
    data = kite.generate_session(request_token, api_secret=kite_api_secret)
    access_token = data["access_token"]
    save_access_token(access_token)

    return redirect(url_for('dashboard'))

@app.route("/dashboard")
def dashboard():
    access_token = load_access_token()
    return login_template.format(
        access_token=access_token,
        user_data=json.dumps(
            {"access_token": access_token},
            indent=4,
            sort_keys=True,
            default=serializer
        )
    )

@app.route("/holdings.json")
def holdings():
    kite = get_kite_client()
    return jsonify(holdings=kite.holdings())

@app.route("/orders.json")
def orders():
    kite = get_kite_client()
    return jsonify(orders=kite.orders())

if __name__ == "__main__":
    logging.info(f"Starting server: http://{HOST}:{PORT}")
    app.run(host=HOST, port=PORT, debug=True)
  
