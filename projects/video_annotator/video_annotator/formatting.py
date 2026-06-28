from __future__ import annotations

import json

from video_annotator.types import AnswerFormat


def coerce_format(raw_answer: str, answer_format: AnswerFormat) -> str:
    """Make sure the answer actually conforms to the requested format.

    Only JSON needs enforcing -- text/markdown/bullets are free-form prose and
    whatever the model returns is valid for them.
    """
    if answer_format != AnswerFormat.JSON:
        return raw_answer
    text = raw_answer.strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        # Model didn't return clean JSON -- wrap it so callers can still rely on the format.
        return json.dumps({"answer": raw_answer})
