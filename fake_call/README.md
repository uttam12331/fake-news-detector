# Fake Call

A "fake call me" app: type any caller name, pick a delay, and your browser
simulates an incoming call from that name — synthesized ringtone, vibration
(on supported devices), and full-screen incoming-call / in-call UI. Nothing
is recorded or sent anywhere; it's all simulated client-side in this tab.

## Run

```bash
pip install -r requirements.txt
python -m flask --app app.server run --port 5057
```

Open `http://localhost:5057`. A server is only needed because Service
Workers/Wake Lock require a secure context (`http://localhost` qualifies;
`file://` does not) — there's no backend logic beyond serving the page.

## Install on your phone (PWA)

Open the URL on your phone's browser (same Wi-Fi network, use your
computer's LAN IP instead of `localhost`), then "Add to Home Screen" —
it installs and launches full-screen like a native app.

## How it works

- **Caller name / label** — shown on both the incoming-call and in-call screens.
- **Delay** — "Right now" or a countdown (5s/10s/30s/1m/custom), with a
  Cancel option while it's pending, so you have time to set the scene.
- **Ringtone** — generated on the fly with the Web Audio API (no audio file
  shipped), looping every ~2s until accepted or declined.
- **Vibration** — uses the Vibration API where supported.
- **Accept** moves to an in-call screen with a live timer and cosmetic
  mute/keypad/speaker buttons (there's no real call, so these just toggle
  a pressed look). **Decline** or **End call** return to setup.

## Tests

```bash
node tests/test_callsim.mjs
```
