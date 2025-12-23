import json
import os
import shutil
import subprocess
import tempfile
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

        # Internal pipeline (if provided) -> DEPRECATED
        if self.diffsinger_pipeline is not None:
            self.log("Using internal DiffSinger pipeline object.")
            input_dict = ds_input.to_dict()
            try:
                audio_output = self.diffsinger_pipeline.infer(input_dict)
                if output_path:
                    self._save_audio(audio_output, output_path)
                    return output_path
                return audio_output
            except Exception as e:
                self.log(f"Internal synthesis failed: {e}", "error")
                raise

        # External subprocess (Default)
        self.log("Using external DiffSinger subprocess.")
        return self._synthesize_subprocess(ds_input, output_path)

    def _synthesize_subprocess(self, ds_input: DiffSingerInput, output_path: str) -> str:
        """Execute DiffSinger as a subprocess"""
        ext_config = self.config.synthesis.external

        # Validate paths
        ds_root = os.path.abspath(ext_config.project_root)
        script_path = os.path.join(ds_root, ext_config.script_path)

        if not os.path.exists(ds_root):
            raise FileNotFoundError(f"DiffSinger root not found at: {ds_root}")
        if not os.path.exists(script_path):
            raise FileNotFoundError(f"DiffSinger script not found at: {script_path}")

        # Create temporary input JSON
        # We must close the file so the subprocess can read it
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as tmp:
            json.dump(ds_input.to_dict(), tmp, ensure_ascii=False)
            tmp_input_path = tmp.name

        try:
            # Construct command
            # Note: We do NOT pass --output_file because ds_e2e.py hardcodes the output to infer_out/example_out.wav
            cmd = [
                ext_config.python_path,
                script_path,
                "--config", ext_config.config_path,
                "--exp_name", ext_config.exp_name,
                "--input_file", tmp_input_path
            ]

            self.log(f"Executing command in {ds_root}:")
            self.log(f"Cmd: {' '.join(cmd)}")

            # Prepare environment variables (PYTHONPATH is crucial for DiffSinger internal imports)
            env = os.environ.copy()
            env["PYTHONPATH"] = ds_root
            if "CUDA_VISIBLE_DEVICES" not in env:
                env["CUDA_VISIBLE_DEVICES"] = "0"

            result = subprocess.run(
                cmd,
                cwd=ds_root,
                capture_output=True,
                text=True,
                env=env
            )

            if result.stdout:
                self.log(f"DiffSinger STDOUT:\n{result.stdout[-500:]}...", level="info")  # Log last 500 chars

            if result.returncode != 0:
                self.log(f"DiffSinger process failed with code {result.returncode}", "error")
                self.log(f"DiffSinger STDERR:\n{result.stderr}", "error")
                raise RuntimeError("DiffSinger subprocess execution failed.")

            # DiffSinger E2E example saves to: {ds_root}/infer_out/example_out.wav
            default_output_location = os.path.join(ds_root, "infer_out", "example_out.wav")

            if not os.path.exists(default_output_location):
                self.log(f"Expected output file not found at: {default_output_location}", "error")
                if result.stderr:
                    self.log(f"Full STDERR: {result.stderr}", "error")
                raise RuntimeError("DiffSinger finished but output file was not created.")

            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            shutil.copy2(default_output_location, output_path)
            self.log(f"Successfully synthesized audio to: {output_path}")

            return output_path

        finally:
            # clean up temp input file
            if os.path.exists(tmp_input_path):
                os.unlink(tmp_input_path)

    def _save_audio(self, audio_data, output_path: str):
        """Save audio data to file (used only for internal pipeline)"""
        import soundfile as sf
        import numpy as np

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        if isinstance(audio_data, dict):
            audio = audio_data.get("audio", audio_data.get("wav"))
            sr = audio_data.get("sample_rate", audio_data.get("sr", 44100))
        elif isinstance(audio_data, tuple):
            audio, sr = audio_data
        else:
            audio = audio_data
            sr = self.config.synthesis.sample_rate

        if not isinstance(audio, np.ndarray):
            audio = np.array(audio)

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
        result_path = self.synthesize(ds_input, output_path)

        return {
            "diffsinger_input": ds_input,
            "audio_path": result_path,
            "audio_data": None
        }
