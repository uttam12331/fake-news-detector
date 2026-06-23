from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class AnswerType(str, Enum):
    DESCRIPTION = "description"   # general "what's in this video" summary
    SUMMARY = "summary"           # condensed summary
    QA = "qa"                     # answer to a specific question
    TIMELINE = "timeline"         # chronological breakdown by timestamp
    FACT_CHECK = "fact_check"     # verdict-style claim check against video content


class AnswerFormat(str, Enum):
    TEXT = "text"
    MARKDOWN = "markdown"
    BULLETS = "bullets"
    JSON = "json"


@dataclass
class FrameCaption:
    timestamp_s: float
    caption: str


@dataclass
class VideoContext:
    """Everything extracted from a video before any question is asked."""

    video_path: str
    duration_s: float
    frame_captions: list[FrameCaption] = field(default_factory=list)
    transcript: str = ""

    def render(self) -> str:
        """Flatten frames + transcript into a single text context for the LLM prompt."""
        lines = [f"Video duration: {self.duration_s:.1f}s"]
        if self.transcript.strip():
            lines.append("\n--- Audio transcript ---")
            lines.append(self.transcript.strip())
        if self.frame_captions:
            lines.append("\n--- Visual scene-by-scene (sampled frames) ---")
            for fc in self.frame_captions:
                lines.append(f"[{fc.timestamp_s:6.1f}s] {fc.caption}")
        return "\n".join(lines)


@dataclass
class BaseAnswer:
    answer: str
    answer_type: AnswerType
    answer_format: AnswerFormat
    question: str | None
    instructions: str | None


@dataclass
class VideoAnswer(BaseAnswer):
    frames_analyzed: int = 0
    had_transcript: bool = False


@dataclass
class TranscriptSegment:
    start_s: float
    end_s: float
    text: str


@dataclass
class AudioContext:
    """Everything extracted from an audio file before any question is asked."""

    audio_path: str
    duration_s: float
    segments: list[TranscriptSegment] = field(default_factory=list)

    @property
    def transcript(self) -> str:
        return " ".join(seg.text.strip() for seg in self.segments).strip()

    def render(self) -> str:
        lines = [f"Audio duration: {self.duration_s:.1f}s"]
        if self.segments:
            lines.append("\n--- Transcript (timestamped) ---")
            for seg in self.segments:
                lines.append(f"[{seg.start_s:6.1f}s-{seg.end_s:6.1f}s] {seg.text.strip()}")
        else:
            lines.append("\n(no speech detected)")
        return "\n".join(lines)


@dataclass
class AudioAnswer(BaseAnswer):
    segments_analyzed: int = 0


@dataclass
class ImageAnswer(BaseAnswer):
    pass
