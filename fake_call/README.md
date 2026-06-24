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
- **Fake voice** — when you accept, an optional toggle has the "other side"
  speak generic filler lines via the Web Speech Synthesis API, with randomized
  pauses, so it sounds like an actual back-and-forth.
- **Status bar** — a cosmetic clock/signal/battery row on the call screens
  for realism; sizing uses `clamp()`/viewport units so it looks right across
  phone sizes.
- **Accept** moves to an in-call screen with a live timer and cosmetic
  mute/keypad/speaker buttons (there's no real call, so these just toggle
  a pressed look). **Decline** or **End call** return to setup.

## Check a number

A second tab does a phone-number lookup — carrier, line type, country and
rough location, using a Numverify-compatible API with **your own API key**
(pasted into Settings, stored only in this browser/device). This is *not* a
Truecaller-style name lookup: no free or legal API exposes that crowd-sourced
identity data, so this only surfaces what a legitimate phone-validation API
actually returns.

The web app proxies the request through its own `/api/lookup` route (the
provider has no CORS support, so the browser can't call it directly). The
Android wrapper has no backend, so it calls the provider straight from native
code instead, via a small JS↔Java bridge (`MainActivity.LookupBridge`).

## Android app (.apk)

`android/` is a minimal WebView wrapper around this same web app (the JS/CSS
in `app/static` is copied into it at build time — one UI, two shells). Build
it with:

```bash
cd android && ./gradlew assembleDebug
```

or just push to this branch — the `Build Fake Call APK` GitHub Actions
workflow builds it automatically and uploads `app-debug.apk` as a workflow
artifact (this sandbox can't build it locally: the Android SDK's Maven host
is blocked by this environment's egress policy).

## Tests

```bash
node tests/test_callsim.mjs
node tests/test_fakevoice.mjs
python -m pytest tests/test_lookup.py
```
