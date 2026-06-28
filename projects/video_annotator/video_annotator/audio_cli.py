from __future__ import annotations

import sys

from video_annotator.audio_annotator import AudioAnnotator
from video_annotator.cli_common import apply_model_overrides, build_parser
from video_annotator.config import AnnotatorConfig


def main(argv: list[str] | None = None) -> int:
    parser = build_parser(
        "audio-annotator",
        "Ask questions about an audio recording, or get a description of it, using a local LLM.",
        "audio", "Path to an audio file",
    )
    args = parser.parse_args(argv)

    config = AnnotatorConfig()
    apply_model_overrides(config, args)

    result = AudioAnnotator(config).ask(
        args.audio,
        question=args.question,
        instructions=args.instructions,
        answer_type=args.type,
        answer_format=args.format,
    )
    print(result.answer)
    print(
        f"\n[type={result.answer_type.value} format={result.answer_format.value} "
        f"segments={result.segments_analyzed}]",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
