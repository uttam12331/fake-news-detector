from __future__ import annotations

import argparse
import sys

from video_annotator.annotator import VideoAnnotator
from video_annotator.config import AnnotatorConfig


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="video-annotator",
        description="Ask questions about a video, or get a description of it, using a local LLM.",
    )
    parser.add_argument("video", help="Path to a video file")
    parser.add_argument("-q", "--question", help="A specific question about the video")
    parser.add_argument("-i", "--instructions", help="How to frame the answer, e.g. 'focus on safety'")
    parser.add_argument(
        "-t", "--type", default="description",
        choices=["description", "summary", "qa", "timeline", "fact_check"],
    )
    parser.add_argument(
        "-f", "--format", default="text", choices=["text", "markdown", "bullets", "json"],
    )
    parser.add_argument("--vision-model", default=None, help="Ollama model for frame captioning")
    parser.add_argument("--text-model", default=None, help="Ollama model for the final answer")
    parser.add_argument("--ollama-host", default=None)
    args = parser.parse_args(argv)

    config = AnnotatorConfig()
    if args.vision_model:
        config.vision_model = args.vision_model
    if args.text_model:
        config.text_model = args.text_model
    if args.ollama_host:
        config.ollama_host = args.ollama_host

    annotator = VideoAnnotator(config)
    result = annotator.ask(
        args.video,
        question=args.question,
        instructions=args.instructions,
        answer_type=args.type,
        answer_format=args.format,
    )
    print(result.answer)
    print(
        f"\n[type={result.answer_type.value} format={result.answer_format.value} "
        f"frames={result.frames_analyzed} transcript={'yes' if result.had_transcript else 'no'}]",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
