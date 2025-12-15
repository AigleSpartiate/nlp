import logging
import os
from typing import Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class AudioMixer:
    """Utility for mixing MIDI and vocal audio tracks"""

    def __init__(
            self,
            sample_rate: int = 44100,
            soundfont_path: Optional[str] = None
    ):
        self.sample_rate = sample_rate
        self.soundfont_path = soundfont_path or self._find_default_soundfont()

    def _find_default_soundfont(self) -> Optional[str]:
        """Find a default soundfont on the system"""
        common_paths = [
            "/usr/share/sounds/sf2/FluidR3_GM.sf2",
            "/usr/share/soundfonts/FluidR3_GM.sf2",
            "/usr/share/sounds/sf2/default.sf2",
            "~/.fluidsynth/default_sound_font.sf2",
            "C:/soundfonts/FluidR3_GM.sf2",
            "/usr/local/share/fluidsynth/FluidR3_GM.sf2",
            "/opt/homebrew/share/fluidsynth/FluidR3_GM.sf2",
        ]

        for path in common_paths:
            expanded = os.path.expanduser(path)
            if os.path.exists(expanded):
                logger.info(f"Found soundfont: {expanded}")
                return expanded

        logger.warning("No default soundfont found. MIDI rendering may fail.")
        return None

    def _ensure_1d_float_array(self, audio: np.ndarray, name: str = "audio") -> np.ndarray:
        """
        Ensure audio is a 1D float array.
        Handles stereo, nested arrays, and type conversion.
        """
        # Convert to numpy array if not already
        if not isinstance(audio, np.ndarray):
            audio = np.array(audio)

        # Log original shape for debugging
        logger.debug(f"{name} original shape: {audio.shape}, dtype: {audio.dtype}")

        # Flatten if needed (handles deeply nested arrays)
        if audio.ndim > 2:
            logger.warning(f"{name} has {audio.ndim} dimensions, flattening...")
            audio = audio.flatten()

        # Handle stereo (2D) audio - convert to mono
        if audio.ndim == 2:
            if audio.shape[0] == 2:
                # Shape is (2, samples) - channels first
                audio = np.mean(audio, axis=0)
            elif audio.shape[1] == 2:
                # Shape is (samples, 2) - channels last
                audio = np.mean(audio, axis=1)
            elif audio.shape[0] < audio.shape[1]:
                # Likely (channels, samples)
                audio = np.mean(audio, axis=0)
            else:
                # Likely (samples, channels)
                audio = np.mean(audio, axis=1)

        # Ensure 1D
        audio = audio.flatten()

        # Ensure float type
        if not np.issubdtype(audio.dtype, np.floating):
            audio = audio.astype(np.float64)

        # Normalize to [-1, 1] if needed
        max_val = np.max(np.abs(audio))
        if max_val > 1.0:
            # Likely int16 or similar
            if max_val > 32767:
                audio = audio / 32768.0  # int16 range
            elif max_val > 1.0:
                audio = audio / max_val

        logger.debug(f"{name} final shape: {audio.shape}, dtype: {audio.dtype}")
        return audio

    def midi_to_audio(
            self,
            midi_path: str,
            output_path: Optional[str] = None,
            soundfont_path: Optional[str] = None
    ) -> Tuple[np.ndarray, int]:
        """
        Convert MIDI file to audio using FluidSynth.

        Returns:
            Tuple of (audio_array, sample_rate)
        """
        sf_path = soundfont_path or self.soundfont_path

        if not sf_path or not os.path.exists(sf_path):
            raise FileNotFoundError(
                f"Soundfont not found at: {sf_path}. "
                "Please install FluidSynth and a soundfont, or specify soundfont_path. "
                "Try: apt-get install fluidsynth fluid-soundfont-gm"
            )

        logger.info(f"Rendering MIDI with soundfont: {sf_path}")

        # Try using pretty_midi (preferred - pure Python with fluidsynth)
        try:
            audio, sr = self._render_with_pretty_midi(midi_path, sf_path, output_path)
            audio = self._ensure_1d_float_array(audio, "midi_audio")
            return audio, sr
        except ImportError as e:
            logger.debug(f"pretty_midi not available: {e}")
        except Exception as e:
            logger.warning(f"pretty_midi rendering failed: {e}")

        # Fallback to midi2audio
        try:
            audio, sr = self._render_with_midi2audio(midi_path, sf_path, output_path)
            audio = self._ensure_1d_float_array(audio, "midi_audio")
            return audio, sr
        except ImportError as e:
            logger.debug(f"midi2audio not available: {e}")
        except Exception as e:
            logger.warning(f"midi2audio rendering failed: {e}")

        # Fallback to subprocess FluidSynth
        audio, sr = self._render_with_fluidsynth_cli(midi_path, sf_path, output_path)
        audio = self._ensure_1d_float_array(audio, "midi_audio")
        return audio, sr

    def _render_with_pretty_midi(
            self,
            midi_path: str,
            soundfont_path: str,
            output_path: Optional[str] = None
    ) -> Tuple[np.ndarray, int]:
        """Render MIDI using pretty_midi"""
        import pretty_midi

        logger.info("Using pretty_midi for MIDI rendering")
        midi_data = pretty_midi.PrettyMIDI(midi_path)

        # fluidsynth() returns a 1D numpy array
        audio = midi_data.fluidsynth(fs=self.sample_rate, sf2_path=soundfont_path)

        logger.debug(f"pretty_midi output shape: {audio.shape}, dtype: {audio.dtype}")

        if output_path:
            import soundfile as sf
            # Ensure proper format before saving
            audio_to_save = self._ensure_1d_float_array(audio, "save_audio")
            sf.write(output_path, audio_to_save, self.sample_rate)

        return audio, self.sample_rate

    def _render_with_midi2audio(
            self,
            midi_path: str,
            soundfont_path: str,
            output_path: Optional[str] = None
    ) -> Tuple[np.ndarray, int]:
        """Render MIDI using midi2audio"""
        from midi2audio import FluidSynth
        import soundfile as sf
        import tempfile

        logger.info("Using midi2audio for MIDI rendering")

        fs = FluidSynth(soundfont_path, sample_rate=self.sample_rate)

        temp_path = output_path or tempfile.mktemp(suffix='.wav')
        fs.midi_to_audio(midi_path, temp_path)

        audio, sr = sf.read(temp_path)
        logger.debug(f"midi2audio output shape: {audio.shape}, dtype: {audio.dtype}")

        if not output_path:
            os.unlink(temp_path)

        return audio, sr

    def _render_with_fluidsynth_cli(
            self,
            midi_path: str,
            soundfont_path: str,
            output_path: Optional[str] = None
    ) -> Tuple[np.ndarray, int]:
        """Render MIDI using FluidSynth CLI"""
        import subprocess
        import tempfile
        import soundfile as sf

        logger.info("Using FluidSynth CLI for MIDI rendering")

        wav_path = output_path or tempfile.mktemp(suffix='.wav')

        cmd = [
            "fluidsynth",
            "-ni",
            "-g", "1.0",
            "-r", str(self.sample_rate),
            "-o", "audio.file.type=wav",
            "-F", wav_path,
            soundfont_path,
            midi_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"FluidSynth failed: {result.stderr}")

        audio, sr = sf.read(wav_path)
        logger.debug(f"FluidSynth CLI output shape: {audio.shape}, dtype: {audio.dtype}")

        if not output_path:
            os.unlink(wav_path)

        return audio, sr

    def load_audio(self, audio_path: str) -> Tuple[np.ndarray, int]:
        """Load audio file and ensure proper format"""
        import soundfile as sf

        audio, sr = sf.read(audio_path)
        logger.debug(f"Loaded audio shape: {audio.shape}, sr: {sr}")

        audio = self._ensure_1d_float_array(audio, f"loaded_{os.path.basename(audio_path)}")
        return audio, sr

    def normalize_audio(self, audio: np.ndarray, target_db: float = -3.0) -> np.ndarray:
        """Normalize audio to target dB level"""
        audio = self._ensure_1d_float_array(audio, "normalize_input")

        if len(audio) == 0:
            return audio

        peak = np.max(np.abs(audio))
        if peak == 0 or peak < 1e-10:
            return audio

        target_amplitude = 10 ** (target_db / 20)
        return audio * (target_amplitude / peak)

    def match_lengths(
            self,
            audio1: np.ndarray,
            audio2: np.ndarray,
            mode: str = "pad"
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Match the lengths of two audio arrays.
        """
        # Ensure both are 1D first
        audio1 = self._ensure_1d_float_array(audio1, "match_audio1")
        audio2 = self._ensure_1d_float_array(audio2, "match_audio2")

        len1, len2 = len(audio1), len(audio2)

        logger.debug(f"Matching lengths: {len1} vs {len2}")

        if len1 == len2:
            return audio1, audio2

        if mode == "pad":
            target_len = max(len1, len2)
            if len1 < target_len:
                padding = np.zeros(target_len - len1, dtype=audio1.dtype)
                audio1 = np.concatenate([audio1, padding])
            if len2 < target_len:
                padding = np.zeros(target_len - len2, dtype=audio2.dtype)
                audio2 = np.concatenate([audio2, padding])
        else:  # truncate
            target_len = min(len1, len2)
            audio1 = audio1[:target_len]
            audio2 = audio2[:target_len]

        return audio1, audio2

    def mix_tracks(
            self,
            melody_audio: np.ndarray,
            vocal_audio: np.ndarray,
            melody_volume: float = 0.9,
            vocal_volume: float = 1.0,
            normalize_output: bool = True
    ) -> np.ndarray:
        """
        Mix melody and vocal tracks.
        """
        logger.info(f"Mixing tracks - melody_vol: {melody_volume}, vocal_vol: {vocal_volume}")

        # Ensure proper format
        melody_audio = self._ensure_1d_float_array(melody_audio, "melody")
        vocal_audio = self._ensure_1d_float_array(vocal_audio, "vocal")

        logger.debug(f"After ensure_1d - melody: {melody_audio.shape}, vocal: {vocal_audio.shape}")

        # Match lengths
        melody_audio, vocal_audio = self.match_lengths(melody_audio, vocal_audio)

        logger.debug(f"After match_lengths - melody: {melody_audio.shape}, vocal: {vocal_audio.shape}")

        # Apply volumes
        melody_scaled = melody_audio * melody_volume
        vocal_scaled = vocal_audio * vocal_volume

        # Mix
        mixed = melody_scaled + vocal_scaled

        # Normalize to prevent clipping
        if normalize_output:
            mixed = self.normalize_audio(mixed)
        else:
            peak = np.max(np.abs(mixed))
            if peak > 1.0:
                mixed = mixed / peak

        logger.debug(f"Mixed output shape: {mixed.shape}")
        return mixed

    def save_audio(
            self,
            audio: np.ndarray,
            output_path: str,
            sample_rate: Optional[int] = None
    ):
        """Save audio to file"""
        import soundfile as sf

        sr = sample_rate or self.sample_rate

        # Ensure proper format
        audio = self._ensure_1d_float_array(audio, "save_output")

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        sf.write(output_path, audio, sr)
        logger.info(f"Saved audio to: {output_path} (shape: {audio.shape}, sr: {sr})")

    def create_final_mix(
            self,
            midi_path: str,
            vocal_path: str,
            output_path: str,
            melody_volume: float = 0.9,
            vocal_volume: float = 1.0,
            soundfont_path: Optional[str] = None
    ) -> str:
        """
        Create final mixed audio from MIDI and vocal files.
        """
        logger.info(f"Creating final mix: {output_path}")
        logger.info(f"  MIDI: {midi_path}")
        logger.info(f"  Vocal: {vocal_path}")

        # Render MIDI to audio
        logger.info("Rendering MIDI to audio...")
        melody_audio, melody_sr = self.midi_to_audio(
            midi_path,
            soundfont_path=soundfont_path
        )
        logger.info(f"Melody audio: {len(melody_audio)} samples, {melody_sr} Hz")

        # Load vocal audio
        logger.info("Loading vocal audio...")
        vocal_audio, vocal_sr = self.load_audio(vocal_path)
        logger.info(f"Vocal audio: {len(vocal_audio)} samples, {vocal_sr} Hz")

        # Resample if needed
        if melody_sr != vocal_sr:
            logger.info(f"Resampling melody from {melody_sr} to {vocal_sr}")
            melody_audio = self._resample(melody_audio, melody_sr, vocal_sr)
            melody_sr = vocal_sr

        # Mix tracks
        logger.info("Mixing tracks...")
        mixed_audio = self.mix_tracks(
            melody_audio,
            vocal_audio,
            melody_volume=melody_volume,
            vocal_volume=vocal_volume
        )

        # Save output
        self.save_audio(mixed_audio, output_path, vocal_sr)

        return output_path

    def _resample(
            self,
            audio: np.ndarray,
            orig_sr: int,
            target_sr: int
    ) -> np.ndarray:
        """Resample audio to target sample rate"""
        audio = self._ensure_1d_float_array(audio, "resample_input")

        if orig_sr == target_sr:
            return audio

        try:
            import librosa
            resampled = librosa.resample(audio, orig_sr=orig_sr, target_sr=target_sr)
            return self._ensure_1d_float_array(resampled, "resample_output")
        except ImportError:
            logger.warning("librosa not available, using linear interpolation")
            # Simple linear interpolation fallback
            ratio = target_sr / orig_sr
            new_length = int(len(audio) * ratio)
            indices = np.linspace(0, len(audio) - 1, new_length)
            resampled = np.interp(indices, np.arange(len(audio)), audio)
            return resampled
