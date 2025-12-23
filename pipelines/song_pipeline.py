from typing import Optional, Dict

from langchain_core.tools import Tool

from agents import IntegrationAgent
from config import SongComposerConfig
from models.song import Song


class SongPipeline:

    def __init__(
            self,
            config: Optional[SongComposerConfig] = None,
            diffsinger_pipeline=None,
            soundfont_path: Optional[str] = None
    ):
        self.config = config or SongComposerConfig()
        self.integration_agent = IntegrationAgent(
            self.config,
            diffsinger_pipeline=diffsinger_pipeline,
            soundfont_path=soundfont_path or self.config.mixing.soundfont_path
        )

    def set_diffsinger_pipeline(self, pipeline):
        """Set the DiffSinger pipeline for synthesis"""
        self.integration_agent.set_diffsinger_pipeline(pipeline)

    def set_soundfont(self, path: str):
        """Set the soundfont for MIDI rendering"""
        self.integration_agent.set_soundfont(path)

    def compose(
            self,
            lyrics: str,
            title: str = "Untitled",
            synthesize: bool = True,
            export_midi: bool = True,
            create_final_mix: bool = True,
            melody_volume: float = 0.9,
            vocal_volume: float = 1.0
    ) -> Song:
        """
        Compose a song from lyrics.

        Args:
            lyrics: The lyrics text
            title: Song title
            synthesize: Whether to run DiffSinger synthesis
            export_midi: Whether to export MIDI file
            create_final_mix: Whether to create final mixed audio (melody + vocals)
            melody_volume: Volume for melody in final mix
            vocal_volume: Volume for vocals in final mix

        Returns:
            Song object with all outputs
        """
        return self.integration_agent.process(
            lyrics=lyrics,
            title=title,
            synthesize=synthesize,
            export_midi=export_midi,
            create_final_mix=create_final_mix,
            melody_volume=melody_volume,
            vocal_volume=vocal_volume
        )

    def get_diffsinger_input(self, lyrics: str) -> Dict[str, str]:
        """
        Get DiffSinger input format from lyrics.

        Returns:
            Dict with keys: text, notes, notes_duration, input_type
        """
        return self.integration_agent.process_to_diffsinger_input(lyrics)

    def mix_existing_files(
            self,
            midi_path: str,
            vocal_path: str,
            output_path: Optional[str] = None,
            melody_volume: float = 0.9,
            vocal_volume: float = 1.0
    ) -> str:
        """
        Mix existing MIDI and vocal files.

        Useful when you've already generated files separately.
        """
        result = self.integration_agent.mixing_agent.process(
            midi_path=midi_path,
            vocal_path=vocal_path,
            output_path=output_path,
            melody_volume=melody_volume,
            vocal_volume=vocal_volume
        )
        return result["final_audio_path"]

    def as_langchain_tool(self) -> Tool:
        """Get this pipeline as a LangChain Tool."""
        return Tool(
            name="compose_song",
            description="Compose a song from lyrics. Input should be the lyrics text.",
            func=lambda lyrics: self.get_diffsinger_input(lyrics)
        )
