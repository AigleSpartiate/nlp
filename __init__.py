from .agents import (
    LyricAnalysisAgent,
    MelodyGenerationAgent,
    SingingSynthesisAgent,
    IntegrationAgent
)
from .config import SongComposerConfig
from .models import Song, Melody, LyricAnalysis, DiffSingerInput
from .pipelines import SongPipeline

__version__ = "1.0.0"

__all__ = [
    "SongComposerConfig",
    "SongPipeline",
    "LyricAnalysisAgent",
    "MelodyGenerationAgent",
    "SingingSynthesisAgent",
    "IntegrationAgent",
    "Song",
    "Melody",
    "LyricAnalysis",
    "DiffSingerInput"
]
