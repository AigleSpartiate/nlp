import os
from dataclasses import dataclass, field
from enum import Enum
from typing import List


class MusicStyle(Enum):
    POP = "pop"
    BALLAD = "ballad"
    ROCK = "rock"
    FOLK = "folk"
    CLASSICAL = "classical"


class Mood(Enum):
    HAPPY = "happy"
    SAD = "sad"
    ENERGETIC = "energetic"
    CALM = "calm"
    ROMANTIC = "romantic"
    MELANCHOLIC = "melancholic"


@dataclass
class MelodyConfig:
    """Configuration for melody generation"""
    min_note: str = "C3"
    max_note: str = "C6"
    default_tempo: int = 120
    default_time_signature: str = "4/4"
    default_key: str = "C"
    note_duration_range: tuple = (0.2, 0.8)
    rest_probability: float = 0.1

    # valid notes for generation
    valid_notes: List[str] = field(default_factory=lambda: [
        "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"
    ])

    # octave range for vocals
    octave_range: List[int] = field(default_factory=lambda: [3, 4, 5])


@dataclass
class SynthesisConfig:
    """Configuration for singing synthesis"""
    sample_rate: int = 44100
    output_format: str = "wav"
    default_singer: str = "opencpop"


@dataclass
class CerebrasConfig:
    """Configuration for Cerebras API"""
    api_key: str = field(default_factory=lambda: os.getenv("CEREBRAS_API_KEY", ""))
    api_url: str = "https://api.cerebras.ai/v1/chat/completions"
    model: str = "zai-glm-4.6"
    temperature: float = 1.0


@dataclass
class SongComposerConfig:
    """Main configuration class"""
    melody: MelodyConfig = field(default_factory=MelodyConfig)
    synthesis: SynthesisConfig = field(default_factory=SynthesisConfig)
    cerebras: CerebrasConfig = field(default_factory=CerebrasConfig)

    output_dir: str = "./output"
    log_level: str = "INFO"
    language: str = "auto"  # auto, chinese or english

    def __post_init__(self):
        os.makedirs(self.output_dir, exist_ok=True)
