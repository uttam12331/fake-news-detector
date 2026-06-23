from __future__ import annotations

from video_annotator.types import AnswerFormat, AnswerType

FRAME_CAPTION_PROMPT = (
    "Describe exactly what is visible in this single video frame in one or two "
    "plain sentences. Mention people, objects, on-screen text, and actions. "
    "Do not speculate about anything outside the frame."
)

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
    AnswerType.DESCRIPTION: "Give a general description of what happens in the video.",
    AnswerType.SUMMARY: "Give a concise summary of the video's content, no more than a few sentences.",
    AnswerType.QA: "Answer the user's question using only evidence from the video context below.",
    AnswerType.TIMELINE: "Break the video down chronologically: timestamp -> what happens.",
    AnswerType.FACT_CHECK: (
        "Treat the user's question as a claim to verify against the video. State a verdict "
        "(SUPPORTED / CONTRADICTED / NOT ENOUGH EVIDENCE) and the evidence from the video context "
        "that justifies it."
    ),
}


def build_answer_prompt(
    *,
    context_text: str,
    answer_type: AnswerType,
    answer_format: AnswerFormat,
    question: str | None,
    instructions: str | None,
) -> str:
    parts = [
        "You are analyzing a video given the extracted context below (audio transcript "
        "and timestamped visual descriptions of sampled frames). Only use this context -- "
        "do not invent details that aren't supported by it.",
        "",
        "--- VIDEO CONTEXT ---",
        context_text,
        "--- END VIDEO CONTEXT ---",
        "",
        _TYPE_INSTRUCTIONS[answer_type],
        _FORMAT_INSTRUCTIONS[answer_format],
    ]
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
