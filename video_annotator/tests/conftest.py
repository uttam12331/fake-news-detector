import pytest


class FakeBackend:
    """Stands in for OllamaBackend so tests don't need a running Ollama server."""

    def __init__(self, response: str = "a person is talking on camera"):
        self.response = response
        self.images_seen: list[bytes] = []
        self.last_prompt: str | None = None

    def generate_with_image(self, model, image_bytes, prompt):
        self.images_seen.append(image_bytes)
        self.last_prompt = prompt
        return self.response

    def generate(self, model, prompt):
        self.last_prompt = prompt
        return self.response


@pytest.fixture
def fake_backend():
    return FakeBackend()
