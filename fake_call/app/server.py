"""
Fake Call — schedules a simulated incoming phone call with any caller name
you type. Everything (ringtone synthesis, vibration, timers) runs client-side
in the browser; this server only serves the static SPA shell.
"""
import os

import requests
from flask import Flask, jsonify, render_template, request

from . import lookup

HERE = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=os.path.join(HERE, "templates"), static_folder=os.path.join(HERE, "static"))


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/lookup", methods=["POST"])
def api_lookup():
    """Proxies a phone-number validation lookup. Server-side because the
    provider doesn't support CORS for direct browser calls; the user's own
    API key is passed in per-request, never stored."""
    body = request.get_json(silent=True) or {}

    def http_get(url, params):
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()

    try:
        result = lookup.fetch_lookup(body.get("number"), body.get("apiKey"), http_get)
    except ValueError as e:
        return jsonify({"valid": False, "error": str(e)}), 400
    except requests.RequestException:
        return jsonify({"valid": False, "error": "Could not reach the lookup provider."}), 502
    return jsonify(result)


@app.route("/manifest.json")
def manifest():
    return app.send_static_file("manifest.json")


@app.route("/service-worker.js")
def service_worker():
    response = app.send_static_file("service-worker.js")
    response.headers["Service-Worker-Allowed"] = "/"
    return response


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5057)
