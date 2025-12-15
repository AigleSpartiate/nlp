import json
import os
from datetime import datetime
from typing import Dict

from config import SongComposerConfig
from models.lyric_analysis import LyricAnalysis
from models.melody import Melody
from models.song import Song
from .base_agent import BaseAgent
from .lyric_analysis_agent import LyricAnalysisAgent
from .melody_generation_agent import MelodyGenerationAgent
from .singing_synthesis_agent import SingingSynthesisAgent


class IntegrationAgent(BaseAgent):
    """Agent for coordinating the complete workflow"""

    def __init__(
            self,
            config: SongComposerConfig,
            diffsinger_pipeline=None,
            **kwargs
    ):
        super().__init__(config, **kwargs)

        # Initialize sub-agents
        self.lyric_agent = LyricAnalysisAgent(config, self.llm_client)
        self.melody_agent = MelodyGenerationAgent(config, self.llm_client)
        self.synthesis_agent = SingingSynthesisAgent(
            config,
            diffsinger_pipeline=diffsinger_pipeline,
            llm_client=self.llm_client
        )

    @property
    def name(self) -> str:
        return "IntegrationAgent"

    @property
    def description(self) -> str:
        return "Coordinates the complete lyric-to-singing workflow"

    def set_diffsinger_pipeline(self, pipeline):
        """Set the DiffSinger pipeline"""
        self.synthesis_agent.set_pipeline(pipeline)

    def _validate_workflow(
            self,
            analysis: LyricAnalysis,
            melody: Melody
    ) -> tuple[bool, str]:
        """Validate the workflow outputs"""
        # check word count match, if it doesn't match it will be unusable in DiffSinger
        if len(analysis.word_list) != len(melody.word_notes):
            return False, f"Word count mismatch: analysis has {len(analysis.word_list)}, melody has {len(melody.word_notes)}."

        # Validate melody
        is_valid, msg = melody.validate(len(analysis.word_list))
        if not is_valid:
            return False, msg

        return True, "Workflow validation passed."

    def _generate_output_paths(self, title: str) -> Dict[str, str]:
        """Generate output file paths"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(c if c.isalnum() else "_" for c in title)[:20]
        base_name = f"{safe_title}_{timestamp}"

        return {
            "midi": os.path.join(self.config.output_dir, f"{base_name}.mid"),
            "audio": os.path.join(self.config.output_dir, f"{base_name}.{self.config.synthesis.output_format}"),
            "metadata": os.path.join(self.config.output_dir, f"{base_name}_metadata.json")
        }

    def process(
            self,
            lyrics: str,
            title: str = "Untitled",
            synthesize: bool = True,
            export_midi: bool = True
    ) -> Song:
        """Run the complete workflow"""
        self.log("=" * 50)
        self.log(f"Starting song composition: {title}")
        self.log("=" * 50)

        # create song object
        song = Song(lyrics=lyrics, title=title)

        # gen output paths
        paths = self._generate_output_paths(title)

        self.log("Analyzing lyrics...")
        try:
            song.analysis = self.lyric_agent.process(lyrics)
            self.log(f"Analysis complete: {song.analysis.total_words} words, "
                     f"mood={song.analysis.emotional_tone.value}")
        except Exception as e:
            self.log(f"Lyric analysis failed: {e}", "error")
            raise

        self.log("Generating melody...")
        try:
            song.melody = self.melody_agent.process(song.analysis)
            self.log(f"Melody complete: {song.melody.total_duration():.2f}s duration")
        except Exception as e:
            self.log(f"Melody generation failed: {e}", "error")
            raise

        # sanity check
        is_valid, msg = self._validate_workflow(song.analysis, song.melody)
        if not is_valid:
            self.log(f"Workflow validation failed: {msg}", "error")
            raise ValueError(msg)
        self.log("Workflow validation passed")

        # prep DiffSinger input
        self.log("Preparing synthesis input...")
        song.diffsinger_input = self.synthesis_agent.prepare_input(song.melody)

        if export_midi:
            try:
                song.midi_path = song.melody.export_midi(paths["midi"])
                self.log(f"MIDI exported: {song.midi_path}")
            except Exception as e:
                self.log(f"MIDI export failed: {e}", "warning")

        if synthesize:
            self.log("Synthesizing audio...")
            try:
                result = self.synthesis_agent.process(song.melody, paths["audio"])
                song.audio_path = result.get("audio_path")
                self.log(f"Audio synthesized: {song.audio_path}")
            except RuntimeError as e:
                self.log(f"Synthesis skipped: {e}", "warning")
            except Exception as e:
                self.log(f"Synthesis failed: {e}", "error")

        # metadata
        try:
            with open(paths["metadata"], "w", encoding="utf-8") as f:
                json.dump(song.to_dict(), f, ensure_ascii=False, indent=2)
            self.log(f"Metadata saved: {paths['metadata']}")
        except Exception as e:
            self.log(f"Metadata save failed: {e}", "warning")

        self.log("Composition complete.")

        return song

    def process_to_diffsinger_input(self, lyrics: str) -> Dict[str, str]:
        """
        Simplified method to get just the DiffSinger input format.
        Useful when running DiffSinger separately.
        """
        analysis = self.lyric_agent.process(lyrics)
        melody = self.melody_agent.process(analysis)
        ds_input = self.synthesis_agent.prepare_input(melody)
        return ds_input.to_dict()
