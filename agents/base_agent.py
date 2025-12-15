import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

from config import SongComposerConfig
from utils.cerebras_client import CerebrasClient


class BaseAgent(ABC):
    """Base class for all agents."""

    def __init__(
            self,
            config: SongComposerConfig,
            llm_client: Optional[CerebrasClient] = None
    ):
        self.config = config
        self.llm_client = llm_client or CerebrasClient(
            api_key=config.cerebras.api_key,
            model=config.cerebras.model
        )
        self.logger = logging.getLogger(self.__class__.__name__)

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent name"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Agent description"""
        pass

    @abstractmethod
    def process(self, input_data: Any) -> Any:
        """Process input and return output"""
        pass

    def log(self, message: str, level: str = "info"):
        """Log a message"""
        log_func = getattr(self.logger, level, self.logger.info)
        log_func(f"[{self.name}] {message}")
