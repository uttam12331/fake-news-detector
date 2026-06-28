from __future__ import annotations


class OllamaBackend:
    """Thin wrapper around a local Ollama server -- no cloud API calls.

    Requires `ollama serve` running locally with the configured model already
    pulled (e.g. `ollama pull qwen2.5vl:7b`).
    """

    def __init__(self, host: str, timeout_s: float):
        self._host = host
        self._timeout_s = timeout_s
        self._client = None

    def generate_with_image(self, model: str, image_bytes: bytes, prompt: str) -> str:
        """One vision-model call: a single image + a prompt -> text. Used both for
        per-frame captioning (video) and direct image Q&A/description (image)."""
        client = self._get_client()
        response = client.chat(
            model=model,
            messages=[{"role": "user", "content": prompt, "images": [image_bytes]}],
        )
        return response["message"]["content"].strip()

    def generate(self, model: str, prompt: str) -> str:
        client = self._get_client()
        response = client.chat(model=model, messages=[{"role": "user", "content": prompt}])
        return response["message"]["content"].strip()

    def _get_client(self):
        if self._client is None:
            try:
                import ollama
            except ImportError as exc:  # pragma: no cover
                raise ImportError(
                    "The 'ollama' package is required. Install it with: pip install ollama"
                ) from exc
            self._client = ollama.Client(host=self._host, timeout=self._timeout_s)
        return self._client
