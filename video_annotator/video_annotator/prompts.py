from __future__ import annotations

from video_annotator.types import AnswerFormat, AnswerType

FRAME_CAPTION_PROMPT = (
    "Describe exactly what is visible in this single video frame in one or two "
    "plain sentences. Mention people, objects, on-screen text, and actions. "
    "Do not speculate about anything outside the frame."
)

_SUBJECT_INTROS = {
    "video": (
        "You are analyzing a video given the extracted context below (audio transcript "
        "and timestamped visual descriptions of sampled frames). Only use this context -- "
        "do not invent details that aren't supported by it."
    ),
    "audio": (
        "You are analyzing an audio recording given the timestamped transcript below. "
        "Only use this transcript -- do not invent details that aren't supported by it."
    ),
    "image": (
        "You are analyzing the attached image directly. Only describe what is actually "
        "visible -- do not invent details that aren't supported by it."
    ),
}

_FORMAT_INSTRUCTIONS = {
    AnswerFormat.TEXT: "Answer in plain prose, no markdown.",
    AnswerFormat.MARKDOWN: "Answer using markdown (headings/emphasis where useful).",
    AnswerFormat.BULLETS: "Answer as a concise bulleted list, one point per line.",
    AnswerFormat.JSON: (
        "Answer with ONLY a single valid JSON object (no prose, no markdown fences). "
        'Use the shape {"answer": <string or structured value>}.'
    ),
}

_TYPE_INSTRUCTIONS = {
    AnswerType.DESCRIPTION: "Give a general description of what this shows/contains.",
    AnswerType.SUMMARY: "Give a concise summary of the content, no more than a few sentences.",
    AnswerType.QA: "Answer the user's question using only evidence from the content above.",
    AnswerType.TIMELINE: "Break the content down chronologically: timestamp -> what happens.",
    AnswerType.FACT_CHECK: (
        "Treat the user's question as a claim to verify against the content. State a verdict "
        "(SUPPORTED / CONTRADICTED / NOT ENOUGH EVIDENCE) and the evidence above that justifies it."
    ),
}


def build_answer_prompt(
    *,
    subject: str,
    answer_type: AnswerType,
    answer_format: AnswerFormat,
    question: str | None,
    instructions: str | None,
    context_text: str | None = None,
) -> str:
    """Build the final answer prompt for video/audio (with extracted context_text)
    or image (no context_text -- the model sees the image directly in the same call)."""
    parts = [_SUBJECT_INTROS[subject]]
    if context_text:
        label = subject.upper()
        parts += ["", f"--- {label} CONTEXT ---", context_text, f"--- END {label} CONTEXT ---"]
    parts += ["", _TYPE_INSTRUCTIONS[answer_type], _FORMAT_INSTRUCTIONS[answer_format]]
    if question:
        parts.append(f"\nQuestion: {question}")
    if instructions:
        parts.append(f"\nAdditional instructions for how to answer: {instructions}")
    if not question and not instructions:
        parts.append(
            "\nNo specific question or instructions were given, so provide the general "
            "description/summary requested above and say plainly that none were provided."
        )
    return "\n".join(parts)
