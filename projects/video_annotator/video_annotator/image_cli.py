from __future__ import annotations

import sys

from video_annotator.cli_common import apply_model_overrides, build_parser
from video_annotator.config import AnnotatorConfig
from video_annotator.image_annotator import ImageAnnotator


def main(argv: list[str] | None = None) -> int:
    parser = build_parser(
        "image-annotator",
        "Ask questions about an image, or get a description of it, using a local LLM.",
        "image", "Path to an image file",
    )
    args = parser.parse_args(argv)

    config = AnnotatorConfig()
    apply_model_overrides(config, args)

    result = ImageAnnotator(config).ask(
        args.image,
        question=args.question,
        instructions=args.instructions,
        answer_type=args.type,
        answer_format=args.format,
    )
    print(result.answer)
    print(
        f"\n[type={result.answer_type.value} format={result.answer_format.value}]",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
