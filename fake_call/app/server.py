"""
Fake Call — schedules a simulated incoming phone call with any caller name
you type. Everything (ringtone synthesis, vibration, timers) runs client-side
in the browser; this server only serves the static SPA shell.
"""
import os

from flask import Flask, render_template

HERE = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=os.path.join(HERE, "templates"), static_folder=os.path.join(HERE, "static"))


@app.route("/")
def index():
    return render_template("index.html")


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
