from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple

from music21 import note as m21_note, stream, midi, tempo, meter, key as m21_key


@dataclass
class NoteEvent:
    """A single note event in the melody"""
    pitch: str  # Standard format: "C4", "F#4", "rest" (NOT DiffSinger format)
    duration: float  # in seconds
    word_index: int  # corresponding word in lyrics
    is_rest: bool = False
    velocity: int = 80
    is_slur: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pitch": self.pitch,
            "duration": self.duration,
            "word_index": self.word_index,
            "is_rest": self.is_rest,
            "velocity": self.velocity,
            "is_slur": self.is_slur
        }

    @property
    def note_name(self) -> str:
        """Get note name without octave"""
        if self.is_rest:
            return "rest"
        # Handle both "F#5" and potential "F#/Gb5" format
        if "/" in self.pitch:
            return self.pitch.split("/")[0]
        return self.pitch[:-1]

    @property
    def octave(self) -> Optional[int]:
        """Get octave number"""
        if self.is_rest:
            return None
        return int(self.pitch[-1])

    def get_pitch_for_midi(self) -> str:
        """Get pitch in standard format for MIDI/music21"""
        from utils.music_utils import MusicUtils
        return MusicUtils.from_diffsinger_format(self.pitch)

    def get_pitch_for_diffsinger(self) -> str:
        """Get pitch in DiffSinger enharmonic format"""
        from utils.music_utils import MusicUtils
        return MusicUtils.format_note_for_diffsinger(self.pitch)


@dataclass
class WordNotes:
    """Notes assigned to a single word"""
    word: str
    word_index: int
    notes: List[NoteEvent] = field(default_factory=list)

    def get_notes_string(self, for_diffsinger: bool = True) -> str:
        """Get notes as space-separated string"""
        if for_diffsinger:
            return " ".join(n.get_pitch_for_diffsinger() for n in self.notes)
        else:
            return " ".join(n.get_pitch_for_midi() for n in self.notes)

    def get_durations_string(self) -> str:
        """Get durations in DiffSinger format (space-separated)"""
        return " ".join(f"{n.duration:.6f}" for n in self.notes)

    def total_duration(self) -> float:
        return sum(n.duration for n in self.notes)


@dataclass
class Melody:
    """Complete melody representation"""
    word_notes: List[WordNotes] = field(default_factory=list)
    tempo: int = 120
    key_signature: str = "C"
    time_signature: str = "4/4"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "word_notes": [
                {
                    "word": wn.word,
                    "word_index": wn.word_index,
                    "notes": [n.to_dict() for n in wn.notes]
                }
                for wn in self.word_notes
            ],
            "tempo": self.tempo,
            "key_signature": self.key_signature,
            "time_signature": self.time_signature
        }

    def to_diffsinger_format(self) -> Dict[str, str]:
        """Convert melody to DiffSinger input format"""
        text = "".join(wn.word for wn in self.word_notes)

        notes_parts = []
        durations_parts = []

        for wn in self.word_notes:
            # use DiffSinger format for notes
            notes_parts.append(wn.get_notes_string(for_diffsinger=True))
            durations_parts.append(wn.get_durations_string())

        return {
            "text": text,
            "notes": " | ".join(notes_parts),
            "notes_duration": " | ".join(durations_parts),
            "input_type": "word"
        }

    def get_all_notes(self) -> List[NoteEvent]:
        """Get all note events in order"""
        all_notes = []
        for wn in self.word_notes:
            all_notes.extend(wn.notes)
        return all_notes

    def to_music21_stream(self) -> stream.Stream:
        """Convert to music21 stream for MIDI export"""
        s = stream.Stream()

        # add tempo
        s.append(tempo.MetronomeMark(number=self.tempo))

        # add key signature + handle potential issues
        try:
            key_sig = self.key_signature
            # clean up key signature if needed
            if "/" in key_sig:
                key_sig = key_sig.split("/")[0]
            s.append(m21_key.Key(key_sig))
        except Exception as e:
            # Fallback to C major
            s.append(m21_key.Key("C"))

        # add time signature
        s.append(meter.TimeSignature(self.time_signature))

        # add notes
        for note_event in self.get_all_notes():
            if note_event.is_rest:
                n = m21_note.Rest()
            else:
                # MIDI-compatible format (not DiffSinger format)
                note_pitch = note_event.get_pitch_for_midi()
                try:
                    n = m21_note.Note(note_pitch)
                    n.volume.velocity = note_event.velocity
                except Exception as e:
                    # Fallback to C4 if note parsing fails
                    n = m21_note.Note("C4")
                    n.volume.velocity = note_event.velocity

            # convert duration from seconds to quarter notes
            quarter_note_duration = 60.0 / self.tempo
            n.quarterLength = note_event.duration / quarter_note_duration

            s.append(n)

        return s

    def export_midi(self, filepath: str) -> str:
        """Export melody to MIDI file"""
        import os
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)

        s = self.to_music21_stream()
        mf = midi.translate.music21ObjectToMidiFile(s)
        mf.open(filepath, 'wb')
        mf.write()
        mf.close()
        return filepath

    def total_duration(self) -> float:
        """Get total duration in seconds"""
        return sum(wn.total_duration() for wn in self.word_notes)

    def validate(self, word_count: int) -> Tuple[bool, str]:
        """Validate melody against expected word count"""
        if len(self.word_notes) != word_count:
            return False, f"Word count mismatch: expected {word_count}, got {len(self.word_notes)}"

        for wn in self.word_notes:
            if not wn.notes:
                return False, f"No notes assigned to word '{wn.word}' at index {wn.word_index}"

        return True, "Melody is valid"
