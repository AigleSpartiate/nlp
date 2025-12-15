import json
import random
import re
from typing import List, Tuple

from models.lyric_analysis import LyricAnalysis
from models.melody import Melody, NoteEvent, WordNotes
from utils.music_utils import MusicUtils
from .base_agent import BaseAgent


class MelodyGenerationAgent(BaseAgent):
    """Agent for generating melodies"""

    @property
    def name(self) -> str:
        return "MelodyGenerationAgent"

    @property
    def description(self) -> str:
        return "Generates melody based on lyric analysis using LLM and music theory"

    def _get_melody_prompt(
            self,
            analysis: LyricAnalysis,
            num_words: int
    ) -> str:
        """Generate prompt for melody generation"""
        scale_type = MusicUtils.get_scale_for_mood(analysis.emotional_tone.value)
        key = analysis.suggested_key.replace("m", "").replace("#", "sharp").replace("b", "flat")

        # get available notes in the scale
        scale_notes = MusicUtils.get_scale_notes(key[0] if key else "C", scale_type, 4)
        scale_notes_str = ", ".join(scale_notes)

        return f"""Generate a simple melody for these lyrics.

Lyrics: {analysis.original_text}
Number of words/characters: {num_words}
Mood: {analysis.emotional_tone.value}
Tempo: {analysis.suggested_tempo} BPM
Key: {analysis.suggested_key}
Style: {analysis.suggested_style}

Available notes (scale): {scale_notes_str}
Also available one octave higher: {", ".join([n[:-1] + "5" for n in scale_notes])}

Generate EXACTLY {num_words} notes, one for each word/character.
Use notes from C3 to C6 range.
Format each note as: NoteName+Octave (e.g., C4, G4, E5)

Respond in JSON format:
{{
    "notes": ["C4", "E4", "G4", ...],  // exactly {num_words} notes
    "durations": [0.4, 0.3, 0.5, ...]  // duration in seconds for each note
}}

Respond ONLY with the JSON object."""

    def _parse_melody_response(
            self,
            response: str,
            num_words: int,
            analysis: LyricAnalysis
    ) -> Tuple[List[str], List[float]]:
        """Parse LLM melody response"""
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
                notes = data.get("notes", [])
                durations = data.get("durations", [])

                # pad if needed
                if len(notes) >= num_words and len(durations) >= num_words:
                    return notes[:num_words], durations[:num_words]
        except (json.JSONDecodeError, KeyError):
            pass

        # worst case we fallback (bad)
        self.log("Using rule-based melody generation", "warning")
        return self._generate_rule_based_melody(num_words, analysis)

    def _generate_rule_based_melody(
            self,
            num_words: int,
            analysis: LyricAnalysis
    ) -> Tuple[List[str], List[float]]:
        """Generate melody using music theory rules"""
        # get scale
        key = analysis.suggested_key.replace("m", "")
        scale_type = MusicUtils.get_scale_for_mood(analysis.emotional_tone.value)

        # build notes pool across octaves
        notes_pool = []
        for octave in [4, 5]:
            notes_pool.extend(MusicUtils.get_scale_notes(key[0] if key else "C", scale_type, octave))

        # melodic contour
        contour = MusicUtils.create_melodic_contour(num_words, "wave")

        # map contour to notes
        notes = []
        prev_note_idx = len(notes_pool) // 2  # start in middle

        for i, contour_val in enumerate(contour):
            # move based on contour with some randomness
            step = contour_val - 2 + random.randint(-1, 1)
            new_idx = max(0, min(len(notes_pool) - 1, prev_note_idx + step))
            notes.append(notes_pool[new_idx])
            prev_note_idx = new_idx

        # durations based on tempo
        base_duration = 60.0 / analysis.suggested_tempo
        durations = []

        syllables = analysis.get_all_syllables()
        for i in range(num_words):
            if i < len(syllables):
                # adjust duration based on stress and position
                stress = syllables[i].stress_level
                is_line_end = syllables[i].is_line_end

                duration = base_duration * (0.8 + stress * 0.2)
                if is_line_end:
                    duration *= 1.3  # longer at line ends

                durations.append(round(duration, 6))
            else:
                durations.append(round(base_duration, 6))

        return notes, durations

    def _validate_and_format_note(self, note: str) -> str:
        """Validate and format note for output"""
        if not note or note.lower() == "rest":
            return "rest"

        # extract note name and octave
        match = re.match(r'^([A-Ga-g][#b]?)(\d)$', note)
        if not match:
            return "C4"  # Default

        note_name = match.group(1).upper()
        octave = int(match.group(2))

        # clamp octave to valid range
        octave = max(3, min(6, octave))

        return f"{note_name}{octave}"

    def process(self, analysis: LyricAnalysis) -> Melody:
        """Generate melody from lyric analysis"""
        self.log("Starting melody generation")

        num_words = len(analysis.word_list)
        self.log(f"Generating melody for {num_words} words")

        prompt = self._get_melody_prompt(analysis, num_words)
        try:
            llm_response = self.llm_client.complete(
                prompt,
                system_prompt="You are a music composer. Generate simple, singable melodies. Always respond with valid JSON.",
                temperature=0.8
            )
            notes, durations = self._parse_melody_response(llm_response, num_words, analysis)
        except Exception as e:
            self.log(f"LLM generation failed: {e}, using rule-based", "warning")
            notes, durations = self._generate_rule_based_melody(num_words, analysis)

        # melody structure
        word_notes_list = []

        for i, word in enumerate(analysis.word_list):
            note_str = self._validate_and_format_note(notes[i] if i < len(notes) else "C4")
            duration = durations[i] if i < len(durations) else 0.4

            formatted_note = MusicUtils.format_note_for_diffsinger(note_str)

            note_event = NoteEvent(
                pitch=formatted_note,
                duration=duration,
                word_index=i,
                is_rest=(note_str == "rest")
            )

            word_notes = WordNotes(
                word=word,
                word_index=i,
                notes=[note_event]
            )
            word_notes_list.append(word_notes)

        melody = Melody(
            word_notes=word_notes_list,
            tempo=analysis.suggested_tempo,
            key_signature=analysis.suggested_key,
            time_signature=analysis.suggested_time_signature
        )

        is_valid, msg = melody.validate(num_words)
        if not is_valid:
            self.log(f"Melody validation failed: {msg}", "error")
        else:
            self.log(f"Melody generated: {melody.total_duration():.2f}s total duration")

        return melody
