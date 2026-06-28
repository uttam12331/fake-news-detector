from __future__ import annotations

import sys

from video_annotator.annotator import VideoAnnotator
from video_annotator.cli_common import apply_model_overrides, build_parser
from video_annotator.config import AnnotatorConfig


def main(argv: list[str] | None = None) -> int:
    parser = build_parser(
        "video-annotator",
        "Ask questions about a video, or get a description of it, using a local LLM.",
        "video", "Path to a video file",
    )
    args = parser.parse_args(argv)

    config = AnnotatorConfig()
    apply_model_overrides(config, args)

    result = VideoAnnotator(config).ask(
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
