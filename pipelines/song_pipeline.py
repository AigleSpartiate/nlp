from typing import Optional, Dict

from langchain_core.tools import Tool

from agents import IntegrationAgent
from config import SongComposerConfig
from models.song import Song


class SongPipeline:

    def __init__(
            self,
            config: Optional[SongComposerConfig] = None,
            diffsinger_pipeline=None
    ):
        self.config = config or SongComposerConfig()
        self.integration_agent = IntegrationAgent(
            self.config,
            diffsinger_pipeline=diffsinger_pipeline
        )

    def set_diffsinger_pipeline(self, pipeline):
        """Set the DiffSinger pipeline for synthesis"""
        self.integration_agent.set_diffsinger_pipeline(pipeline)

    def compose(
            self,
            lyrics: str,
            title: str = "Untitled",
            synthesize: bool = True,
            export_midi: bool = True
    ) -> Song:
        """
        Compose a song from lyrics.

        Args:
            lyrics: The lyrics text
            title: Song title
            synthesize: Whether to run DiffSinger synthesis
            export_midi: Whether to export MIDI file

        Returns:
            Song object with all outputs
        """
        return self.integration_agent.process(
            lyrics=lyrics,
            title=title,
            synthesize=synthesize,
            export_midi=export_midi
        )

    def get_diffsinger_input(self, lyrics: str) -> Dict[str, str]:
        """
        Get DiffSinger input format from lyrics.

        Returns:
            Dict with keys: text, notes, notes_duration, input_type
        """
        return self.integration_agent.process_to_diffsinger_input(lyrics)

    def as_langchain_tool(self) -> Tool:
        """
        Get this pipeline as a LangChain Tool.
        """
        return Tool(
            name="compose_song",
            description="Compose a song from lyrics. Input should be the lyrics text.",
            func=lambda lyrics: self.get_diffsinger_input(lyrics)
        )

    def create_langchain_chain(self):
        """
        Create a LangChain chain for the pipeline.
        """
        from langchain_core.runnables import RunnableLambda

        def process_lyrics(input_dict: Dict) -> Dict:
            lyrics = input_dict.get("lyrics", input_dict.get("input", ""))
            return self.get_diffsinger_input(lyrics)

        return RunnableLambda(process_lyrics)
