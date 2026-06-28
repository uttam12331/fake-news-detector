"""Minimal end-to-end example. Requires a running local Ollama server with a
vision model pulled (see README.md "Setup").

Usage: python examples/ask_about_video.py path/to/video.mp4 "your question"
"""
import sys

from video_annotator import AnswerFormat, AnswerType, VideoAnnotator


def main():
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <video_path> [question]")
        raise SystemExit(1)

    video_path = sys.argv[1]
    question = sys.argv[2] if len(sys.argv) > 2 else None

    annotator = VideoAnnotator()
    result = annotator.ask(
        video_path,
        question=question,
        answer_type=AnswerType.QA if question else AnswerType.DESCRIPTION,
        answer_format=AnswerFormat.TEXT,
    )

    print(result.answer)
    print(f"\n(frames analyzed: {result.frames_analyzed}, transcript: {result.had_transcript})")


if __name__ == "__main__":
    main()
