from dataclasses import dataclass
from typing import Dict, Any, Optional

from .lyric_analysis import LyricAnalysis
from .melody import Melody


@dataclass
class DiffSingerInput:
    """Input format for DiffSinger"""
    text: str
    notes: str
    notes_duration: str
    input_type: str = "word"

    def to_dict(self) -> Dict[str, str]:
        return {
            "text": self.text,
            "notes": self.notes,
            "notes_duration": self.notes_duration,
            "input_type": self.input_type
        }

    def validate(self) -> tuple[bool, str]:
        """Validate the input format"""
        # count words (so characters for Chinese)
        word_count = len(self.text)

        # count note groups (separated by |)
        note_groups = [g.strip() for g in self.notes.split("|")]
        duration_groups = [g.strip() for g in self.notes_duration.split("|")]

        if len(note_groups) != word_count:
            return False, f"Note groups ({len(note_groups)}) don't match word count ({word_count})"

        if len(duration_groups) != word_count:
            return False, f"Duration groups ({len(duration_groups)}) don't match word count ({word_count})"

        # check each group has matching notes and durations
        for i, (ng, dg) in enumerate(zip(note_groups, duration_groups)):
            note_count = len(ng.split())
            dur_count = len(dg.split())
            if note_count != dur_count:
                return False, f"Group {i}: note count ({note_count}) != duration count ({dur_count})"

        return True, "Input is valid"


@dataclass
class Song:
    """Complete song representation"""
    lyrics: str
    analysis: Optional[LyricAnalysis] = None
    melody: Optional[Melody] = None
    diffsinger_input: Optional[DiffSingerInput] = None

    # output paths
    midi_path: Optional[str] = None
    audio_path: Optional[str] = None

    # metadata
    title: str = "Untitled"
    style: str = "pop"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "lyrics": self.lyrics,
            "style": self.style,
            "analysis": self.analysis.to_dict() if self.analysis else None,
            "melody": self.melody.to_dict() if self.melody else None,
            "diffsinger_input": self.diffsinger_input.to_dict() if self.diffsinger_input else None,
            "midi_path": self.midi_path,
            "audio_path": self.audio_path
        }

    def is_complete(self) -> bool:
        """Check if song has all required components"""
        return all([
            self.analysis is not None,
            self.melody is not None,
            self.diffsinger_input is not None
        ])
