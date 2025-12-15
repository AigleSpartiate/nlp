import os
from typing import Optional, Dict, Any

from config import SongComposerConfig
from utils.audio_mixer import AudioMixer
from .base_agent import BaseAgent


class AudioMixingAgent(BaseAgent):
    """Agent for mixing melody and vocal tracks"""

    def __init__(
            self,
            config: SongComposerConfig,
            soundfont_path: Optional[str] = None,
            **kwargs
    ):
        super().__init__(config, **kwargs)
        self.mixer = AudioMixer(
            sample_rate=config.synthesis.sample_rate,
            soundfont_path=soundfont_path
        )
        self.soundfont_path = soundfont_path

    @property
    def name(self) -> str:
        return "AudioMixingAgent"

    @property
    def description(self) -> str:
        return "Mixes melody and vocal tracks into final audio"

    def set_soundfont(self, path: str):
        """Set the soundfont path"""
        self.soundfont_path = path
        self.mixer.soundfont_path = path

    def process(
            self,
            midi_path: str,
            vocal_path: str,
            output_path: Optional[str] = None,
            melody_volume: float = 1.0,
            vocal_volume: float = 1.0
    ) -> Dict[str, Any]:
        """
        Mix melody and vocals into final audio.

        Args:
            midi_path: Path to MIDI melody file
            vocal_path: Path to synthesized vocal WAV file
            output_path: Output path for mixed audio
            melody_volume: Volume level for melody (0.0-1.0+)
            vocal_volume: Volume level for vocals (0.0-1.0+)

        Returns:
            Dict with output paths and metadata
        """
        self.log(f"Starting audio mixing")
        self.log(f"  MIDI: {midi_path}")
        self.log(f"  Vocal: {vocal_path}")

        # Validate inputs
        if not os.path.exists(midi_path):
            raise FileNotFoundError(f"MIDI file not found: {midi_path}")
        if not os.path.exists(vocal_path):
            raise FileNotFoundError(f"Vocal file not found: {vocal_path}")

        # Generate output path if not provided
        if output_path is None:
            base_name = os.path.splitext(os.path.basename(midi_path))[0]
            output_path = os.path.join(
                self.config.output_dir,
                f"{base_name}_final.{self.config.synthesis.output_format}"
            )

        try:
            # Create the mix
            result_path = self.mixer.create_final_mix(
                midi_path=midi_path,
                vocal_path=vocal_path,
                output_path=output_path,
                melody_volume=melody_volume,
                vocal_volume=vocal_volume,
                soundfont_path=self.soundfont_path
            )

            self.log(f"Final mix created: {result_path}")

            return {
                "final_audio_path": result_path,
                "midi_path": midi_path,
                "vocal_path": vocal_path,
                "melody_volume": melody_volume,
                "vocal_volume": vocal_volume
            }

        except Exception as e:
            self.log(f"Mixing failed: {e}", "error")
            raise