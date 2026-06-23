"""
Copilot Live — a real-time AI answer assistant (interview/meeting copilot).

This server only serves the static single-page app. All AI calls happen
directly from the browser to the chosen provider (Anthropic / OpenAI) using a
key the user pastes in Settings, which is kept in the browser's localStorage.

Running through this local server (rather than opening the file directly)
matters: microphone, screen-capture and speech-recognition APIs require a
"secure context", which http://localhost satisfies but file:// does not.
"""
import os

from flask import Flask, render_template

HERE = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    template_folder=os.path.join(HERE, "templates"),
    static_folder=os.path.join(HERE, "static"),
)


@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5060, debug=True)
