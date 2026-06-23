from __future__ import annotations

import argparse

from video_annotator.config import AnnotatorConfig


def build_parser(prog: str, description: str, media_arg: str, media_help: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=prog, description=description)
    parser.add_argument(media_arg, help=media_help)
    parser.add_argument("-q", "--question", help="A specific question about the content")
    parser.add_argument("-i", "--instructions", help="How to frame the answer, e.g. 'focus on safety'")
    parser.add_argument(
        "-t", "--type", default="description",
        choices=["description", "summary", "qa", "timeline", "fact_check"],
    )
    parser.add_argument(
        "-f", "--format", default="text", choices=["text", "markdown", "bullets", "json"],
    )
    parser.add_argument("--vision-model", default=None, help="Ollama model for image/frame understanding")
    parser.add_argument("--text-model", default=None, help="Ollama model for the final answer")
    parser.add_argument("--ollama-host", default=None)
    return parser


def apply_model_overrides(config: AnnotatorConfig, args: argparse.Namespace) -> None:
    if args.vision_model:
        config.vision_model = args.vision_model
    if args.text_model:
        config.text_model = args.text_model
    if args.ollama_host:
        config.ollama_host = args.ollama_host
