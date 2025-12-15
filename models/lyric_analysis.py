from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any


class EmotionalTone(Enum):
    JOYFUL = "joyful"
    MELANCHOLIC = "melancholic"
    ENERGETIC = "energetic"
    PEACEFUL = "peaceful"
    ROMANTIC = "romantic"
    ANGRY = "angry"
    NOSTALGIC = "nostalgic"
    HOPEFUL = "hopeful"


@dataclass
class SyllableInfo:
    """Information about a single syllable/word"""
    text: str
    index: int
    syllable_count: int = 1
    stress_level: int = 1  # 1-3, 3 being most stressed
    duration_weight: float = 1.0  # "relative" duration weight
    is_word_end: bool = False
    is_line_end: bool = False
    phonemes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "index": self.index,
            "syllable_count": self.syllable_count,
            "stress_level": self.stress_level,
            "duration_weight": self.duration_weight,
            "is_word_end": self.is_word_end,
            "is_line_end": self.is_line_end,
            "phonemes": self.phonemes
        }


@dataclass
class LineAnalysis:
    """Analysis of a single line of lyrics"""
    text: str
    line_index: int
    syllables: List[SyllableInfo] = field(default_factory=list)
    syllable_count: int = 0
    suggested_measures: int = 1
    is_chorus: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "line_index": self.line_index,
            "syllables": [s.to_dict() for s in self.syllables],
            "syllable_count": self.syllable_count,
            "suggested_measures": self.suggested_measures,
            "is_chorus": self.is_chorus
        }


@dataclass
class LyricAnalysis:
    """Complete lyric analysis result"""
    original_text: str
    language: str

    # structural analysis
    lines: List[LineAnalysis] = field(default_factory=list)
    total_syllables: int = 0
    total_words: int = 0

    # musical suggestions
    suggested_tempo: int = 120
    suggested_key: str = "C"
    suggested_time_signature: str = "4/4"
    suggested_style: str = "pop"

    # emotional analysis
    emotional_tone: EmotionalTone = EmotionalTone.PEACEFUL
    mood_description: str = ""

    # word list for melody mapping
    word_list: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_text": self.original_text,
            "language": self.language,
            "lines": [line.to_dict() for line in self.lines],
            "total_syllables": self.total_syllables,
            "total_words": self.total_words,
            "suggested_tempo": self.suggested_tempo,
            "suggested_key": self.suggested_key,
            "suggested_time_signature": self.suggested_time_signature,
            "suggested_style": self.suggested_style,
            "emotional_tone": self.emotional_tone.value,
            "mood_description": self.mood_description,
            "word_list": self.word_list
        }

    def get_all_syllables(self) -> List[SyllableInfo]:
        """Get all syllables in order"""
        all_syllables = []
        for line in self.lines:
            all_syllables.extend(line.syllables)
        return all_syllables
