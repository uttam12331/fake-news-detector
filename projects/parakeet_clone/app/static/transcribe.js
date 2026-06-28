// Live speech-to-text using the browser's built-in Web Speech API.
// Free, real-time, no key. Works in Chrome/Edge (and Safari with prefix).

export function isSupported() {
  return Boolean(window.SpeechRecognition || window.webkitSpeechRecognition);
}

export class LiveTranscriber {
  // onUpdate(finalText, interimText) fires as speech is recognised.
  constructor({ lang = "en-US", onUpdate, onError, onEnd } = {}) {
    const Impl = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Impl) throw new Error("Speech recognition is not supported in this browser. Use Chrome or Edge.");
    this.recognition = new Impl();
    this.recognition.lang = lang;
    this.recognition.continuous = true;
    this.recognition.interimResults = true;
    this.finalText = "";
    this.listening = false;
    this._wantListening = false;

    this.recognition.onresult = (event) => {
      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const res = event.results[i];
        if (res.isFinal) {
          this.finalText += res[0].transcript;
        } else {
          interim += res[0].transcript;
        }
      }
      if (onUpdate) onUpdate(this.finalText, interim);
    };

    this.recognition.onerror = (e) => {
      if (onError) onError(e.error || "speech-error");
    };

    this.recognition.onend = () => {
      // Chrome stops after a pause; auto-restart while the user still wants to listen.
      if (this._wantListening) {
        try {
          this.recognition.start();
          return;
        } catch (_) {
          /* fallthrough */
        }
      }
      this.listening = false;
      if (onEnd) onEnd(this.finalText);
    };
  }

  start() {
    this.finalText = "";
    this._wantListening = true;
    this.listening = true;
    this.recognition.start();
  }

  stop() {
    this._wantListening = false;
    this.listening = false;
    try {
      this.recognition.stop();
    } catch (_) {
      /* ignore */
    }
    return this.finalText.trim();
  }
}
