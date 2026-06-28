from __future__ import annotations

from video_annotator import image_io, prompts
from video_annotator.config import AnnotatorConfig
from video_annotator.formatting import coerce_format
from video_annotator.types import AnswerFormat, AnswerType, ImageAnswer
from video_annotator.vision_backend import OllamaBackend


class ImageAnnotator:
    """Local-LLM image annotation/Q&A model.

    A single image is sent directly to a local vision-language model (via Ollama)
    together with the question/instructions/type/format -- one call, no intermediate
    captioning step. Nothing leaves the machine; no cloud API calls are made.
    """

    def __init__(self, config: AnnotatorConfig | None = None, backend: OllamaBackend | None = None):
        self.config = config or AnnotatorConfig()
        self.backend = backend or OllamaBackend(self.config.ollama_host, self.config.request_timeout_s)

    def ask(
        self,
        image_path: str,
        *,
        question: str | None = None,
        instructions: str | None = None,
        answer_type: AnswerType | str = AnswerType.DESCRIPTION,
        answer_format: AnswerFormat | str = AnswerFormat.TEXT,
    ) -> ImageAnswer:
        """Answer a question about the image, or describe it if none is given.

        - question: a specific thing to ask about the image content.
        - instructions: how to frame the answer (e.g. "focus on the text on the sign")
          when there isn't a single question.
        - answer_type / answer_format: what kind of answer and in what shape.
        """
        answer_type = AnswerType(answer_type)
        answer_format = AnswerFormat(answer_format)

        if question and answer_type == AnswerType.DESCRIPTION:
            answer_type = AnswerType.QA

        image_bytes = image_io.load_image_bytes(image_path)
        prompt = prompts.build_answer_prompt(
            subject="image",
            answer_type=answer_type,
            answer_format=answer_format,
            question=question,
            instructions=instructions,
        )
        raw_answer = self.backend.generate_with_image(self.config.vision_model, image_bytes, prompt)
        answer = coerce_format(raw_answer, answer_format)

        return ImageAnswer(
            answer=answer,
            answer_type=answer_type,
            answer_format=answer_format,
            question=question,
            instructions=instructions,
        )
