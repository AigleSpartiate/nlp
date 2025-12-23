import json
from typing import List

from music21 import stream, note, chord, instrument, tempo, midi

from models.melody import Melody
from .base_agent import BaseAgent


class AccompanimentAgent(BaseAgent):
    """Agent for generating backing tracks (chords, bass, drums)"""

    @property
    def name(self) -> str:
        return "AccompanimentAgent"

    @property
    def description(self) -> str:
        return "Generates harmonic accompaniment and rhythm"

    def _get_chord_prompt(self, key: str, style: str, num_measures: int) -> str:
        return f"""Generate a chord progression for a song.
Key: {key}
Style: {style}
Length: {num_measures} measures

Respond in JSON format:
{{
    "progression": ["C", "Am", "F", "G", ...] // List of exactly {num_measures} chords
}}
"""

    def _generate_drums(self, score: stream.Score, measures: int, bpm: int):
        """Generate a basic drum beat"""
        drum_part = stream.Part()
        drum_part.insert(0, instrument.Percussion())

        # some default rock/pop beat
        for m in range(measures):
            # Kick (MIDI 36) on beat 1 and 3
            k1 = note.Note(36);
            k1.quarterLength = 1;
            drum_part.append(k1)

            # Snare (MIDI 38) on beat 2
            s1 = note.Note(38);
            s1.quarterLength = 1;
            drum_part.append(s1)

            # Kick on beat 3
            k2 = note.Note(36);
            k2.quarterLength = 1;
            drum_part.append(k2)

            # Snare on beat 4
            s2 = note.Note(38);
            s2.quarterLength = 1;
            drum_part.append(s2)

        score.insert(0, drum_part)

    def _generate_bass(self, score: stream.Score, chords_list: List[str]):
        """Generate a simple bass line (Root notes)"""
        bass_part = stream.Part()
        bass_part.insert(0, instrument.ElectricBass())

        for chord_name in chords_list:
            # Parse chord to get root
            try:
                c = chord.Chord(chord_name)
                root_note = c.root().name

                # Bass plays root note, octave 2
                n = note.Note(f"{root_note}2")
                n.quarterLength = 4  # Whole note
                bass_part.append(n)
            except:
                bass_part.append(note.Rest(quarterLength=4))

        score.insert(0, bass_part)

    def _generate_chords(self, score: stream.Score, chords_list: List[str], style: str):
        """Generate piano/pad accompaniment"""
        piano_part = stream.Part()
        piano_part.insert(0, instrument.ElectricPiano())

        for chord_name in chords_list:
            try:
                # Create chord object, move to middle octave
                c = chord.Chord(chord_name)
                c.closedPosition(forceOctave=4, inPlace=True)

                if style == "rock" or style == "pop":
                    # Rhythmic chords (Quarter notes)
                    for _ in range(4):
                        new_c = chord.Chord(c)
                        new_c.quarterLength = 1
                        new_c.volume.velocity = 60  # Softer than melody
                        piano_part.append(new_c)
                else:
                    # Sustained chords (Whole note)
                    c.quarterLength = 4
                    c.volume.velocity = 50
                    piano_part.append(c)
            except:
                piano_part.append(note.Rest(quarterLength=4))

        score.insert(0, piano_part)

    def process(self, melody: Melody, output_path: str) -> str:
        self.log("Generating accompaniment...")

        # Song length in measures
        # TODO: Assuming 4/4 time for simplicity (to fix)
        total_seconds = melody.total_duration()
        beats = (total_seconds / 60) * melody.tempo
        measures = int(beats / 4) + 2  # add buffer

        # Get chords from LLM
        prompt = self._get_chord_prompt(melody.key_signature, "pop", measures)
        try:
            resp = self.llm_client.complete(prompt, temperature=1.0)
            data = json.loads(resp.replace("```json", "").replace("```", ""))
            chords_list = data.get("progression", ["C"] * measures)
        except Exception as e:
            self.log(f"Chord generation failed, using default: {e}", "warning")
            chords_list = [melody.key_signature] * measures

        # create multi-track score
        score = stream.Score()
        score.insert(0, tempo.MetronomeMark(number=melody.tempo))

        # Add the original melody (lead)
        # reconstruct the melody part from Melody object
        melody_part = melody.to_music21_stream()
        melody_part.insert(0, instrument.Oboe())  # to make melody stand out
        score.insert(0, melody_part)

        # Backing Tracks (drums + bass NOT llm generated, the results are too bad)
        self._generate_drums(score, measures, melody.tempo)
        self._generate_bass(score, chords_list)
        self._generate_chords(score, chords_list, "pop")

        # export + close
        mf = midi.translate.music21ObjectToMidiFile(score)
        mf.open(output_path, 'wb')
        mf.write()
        mf.close()

        return output_path
