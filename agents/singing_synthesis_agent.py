import os
from typing import Optional, Dict, Any

from config import SongComposerConfig
from models.melody import Melody
from models.song import DiffSingerInput
from .base_agent import BaseAgent


class SingingSynthesisAgent(BaseAgent):
    """Agent for singing synthesis using DiffSinger"""

    def __init__(
            self,
            config: SongComposerConfig,
            diffsinger_pipeline=None,
            **kwargs
    ):
        super().__init__(config, **kwargs)
        self.diffsinger_pipeline = diffsinger_pipeline

    @property
    def name(self) -> str:
        return "SingingSynthesisAgent"

    @property
    def description(self) -> str:
        return "Converts melody and lyrics into synthesized singing using DiffSinger"

    def set_pipeline(self, pipeline):
        """Set the DiffSinger pipeline"""
        self.diffsinger_pipeline = pipeline

    def prepare_input(self, melody: Melody) -> DiffSingerInput:
        """Prepare input in DiffSinger format"""
        diffsinger_format = melody.to_diffsinger_format()

        ds_input = DiffSingerInput(
            text=diffsinger_format["text"],
            notes=diffsinger_format["notes"],
            notes_duration=diffsinger_format["notes_duration"],
            input_type="word"
        )

        is_valid, msg = ds_input.validate()
        if not is_valid:
            self.log(f"DiffSinger input validation failed: {msg}", "error")
            raise ValueError(msg)

        self.log(f"Prepared DiffSinger input: {len(ds_input.text)} characters")
        return ds_input

    def synthesize(
            self,
            ds_input: DiffSingerInput,
            output_path: Optional[str] = None
    ) -> str:
        """Synthesize audio using DiffSinger"""
        if self.diffsinger_pipeline is None:
            raise RuntimeError("DiffSinger pipeline not set. Call set_pipeline() first.")

        self.log("Starting synthesis.")

        # prep input dict for DiffSinger
        input_dict = ds_input.to_dict()

        try:
            audio_output = self.diffsinger_pipeline.infer(input_dict)

            if output_path:
                self._save_audio(audio_output, output_path)
                self.log(f"Audio saved to: {output_path}")
                return output_path

            return audio_output

        except Exception as e:
            self.log(f"Synthesis failed: {e}", "error")
            raise

    def _save_audio(self, audio_data, output_path: str):
        """Save audio data to file"""
        import soundfile as sf
        import numpy as np

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        # to handle different audio data formats
        if isinstance(audio_data, dict):
            # if DiffSinger returns dict with audio and sample rate
            audio = audio_data.get("audio", audio_data.get("wav"))
            sr = audio_data.get("sample_rate", audio_data.get("sr", 44100))
        elif isinstance(audio_data, tuple):
            audio, sr = audio_data
        else:
            audio = audio_data
            sr = self.config.synthesis.sample_rate

        if not isinstance(audio, np.ndarray):
            audio = np.array(audio)

        # normalize audio if needed
        if audio.max() > 1.0 or audio.min() < -1.0:
            audio = audio / max(abs(audio.max()), abs(audio.min()))

        sf.write(output_path, audio, sr)

    def process(self, melody: Melody, output_path: Optional[str] = None) -> Dict[str, Any]:
        """Process melody to generate singing"""
        ds_input = self.prepare_input(melody)

        # gen output path if not specified
        if output_path is None:
            output_path = os.path.join(
                self.config.output_dir,
                f"output.{self.config.synthesis.output_format}"
            )

        # synthesize
        result = self.synthesize(ds_input, output_path)

        return {
            "diffsinger_input": ds_input,
            "audio_path": output_path if isinstance(result, str) else None,
            "audio_data": result if not isinstance(result, str) else None
        }
