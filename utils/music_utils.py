from typing import List, Tuple

from music21 import pitch


class MusicUtils:
    """Utilities for music processing"""

    NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

    # enharmonic equivalents for DiffSinger format
    ENHARMONIC_MAP = {
        "C#": "C#/Db",
        "Db": "C#/Db",
        "D#": "D#/Eb",
        "Eb": "D#/Eb",
        "F#": "F#/Gb",
        "Gb": "F#/Gb",
        "G#": "G#/Ab",
        "Ab": "G#/Ab",
        "A#": "A#/Bb",
        "Bb": "A#/Bb"
    }

    # common scales
    SCALES = {
        "major": [0, 2, 4, 5, 7, 9, 11],
        "minor": [0, 2, 3, 5, 7, 8, 10],
        "pentatonic_major": [0, 2, 4, 7, 9],
        "pentatonic_minor": [0, 3, 5, 7, 10]
    }

    # mood to scale mapping
    MOOD_SCALES = {
        "happy": "major",
        "sad": "minor",
        "energetic": "major",
        "calm": "pentatonic_major",
        "romantic": "major",
        "melancholic": "minor",
        "peaceful": "pentatonic_major"
    }

    @staticmethod
    def note_to_midi(note_name: str) -> int:
        """Convert note name to MIDI number"""
        if note_name.lower() == "rest":
            return -1

        p = pitch.Pitch(note_name)
        return p.midi

    @staticmethod
    def midi_to_note(midi_num: int) -> str:
        """Convert MIDI number to note name"""
        if midi_num < 0:
            return "rest"

        p = pitch.Pitch(midi_num)
        return p.nameWithOctave

    @staticmethod
    def format_note_for_diffsinger(note_name: str) -> str:
        """Format note name for DiffSinger (with enharmonic)"""
        if note_name.lower() == "rest":
            return "rest"

        # extract note and octave
        if len(note_name) == 2:
            base_note = note_name[0]
            octave = note_name[1]
        else:
            base_note = note_name[:-1]
            octave = note_name[-1]

        # enharmonic if needed
        if base_note in MusicUtils.ENHARMONIC_MAP:
            return f"{MusicUtils.ENHARMONIC_MAP[base_note]}{octave}"

        return note_name

    @staticmethod
    def get_scale_notes(root: str, scale_type: str = "major", octave: int = 4) -> List[str]:
        """Get notes in a scale"""
        root_pitch = pitch.Pitch(f"{root}{octave}")
        root_midi = root_pitch.midi

        scale_intervals = MusicUtils.SCALES.get(scale_type, MusicUtils.SCALES["major"])

        notes = []
        for interval_semitones in scale_intervals:
            note_midi = root_midi + interval_semitones
            notes.append(MusicUtils.midi_to_note(note_midi))

        return notes

    @staticmethod
    def get_scale_for_mood(mood: str) -> str:
        """Get appropriate scale type for mood"""
        return MusicUtils.MOOD_SCALES.get(mood.lower(), "major")

    @staticmethod
    def get_vocal_range(voice_type: str = "medium") -> Tuple[int, int]:
        """Get MIDI range for voice type"""
        ranges = {
            "soprano": (60, 84),  # C4 - C6
            "alto": (55, 77),  # G3 - F5
            "tenor": (48, 72),  # C3 - C5
            "bass": (40, 64),  # E2 - E4
            "medium": (55, 77),  # G3 - F5
        }
        return ranges.get(voice_type, ranges["medium"])

    @staticmethod
    def clamp_to_range(midi_note: int, min_note: int, max_note: int) -> int:
        """Clamp a MIDI note to a range, adjusting octave if needed"""
        if midi_note < 0:
            return midi_note  # rest

        while midi_note < min_note:
            midi_note += 12
        while midi_note > max_note:
            midi_note -= 12

        return midi_note

    @staticmethod
    def generate_note_duration(tempo: int, base_duration: str = "quarter") -> float:
        """Generate note duration in seconds"""
        beat_duration = 60.0 / tempo  # seconds per beat

        duration_map = {
            "whole": 4.0,
            "half": 2.0,
            "quarter": 1.0,
            "eighth": 0.5,
            "sixteenth": 0.25
        }

        multiplier = duration_map.get(base_duration, 1.0)
        return beat_duration * multiplier

    @staticmethod
    def suggest_tempo_for_mood(mood: str) -> int:
        """Suggest tempo based on mood"""
        tempo_map = {
            "happy": 120,
            "sad": 72,
            "energetic": 140,
            "calm": 80,
            "romantic": 88,
            "melancholic": 66,
            "peaceful": 76,
            "joyful": 128,
            "nostalgic": 84,
            "hopeful": 100
        }
        return tempo_map.get(mood.lower(), 100)

    @staticmethod
    def create_melodic_contour(
            length: int,
            contour_type: str = "wave"
    ) -> List[int]:
        """Create a melodic contour (relative pitch movements)"""
        if contour_type == "ascending":
            return [i % 5 for i in range(length)]
        elif contour_type == "descending":
            return [(length - i) % 5 for i in range(length)]
        elif contour_type == "wave":
            import math
            return [int(2 * math.sin(i * math.pi / 4) + 2) for i in range(length)]
        elif contour_type == "arch":
            mid = length // 2
            return [min(i, length - 1 - i) for i in range(length)]
        else:
            return [0] * length
