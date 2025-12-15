import logging
import os
from typing import Dict, Optional, List

import requests

logger = logging.getLogger(__name__)


class CerebrasClient:
    """Client for Cerebras API"""

    def __init__(
            self,
            api_key: Optional[str] = None,
            model: str = "zai-glm-4.6",
            api_url: str = "https://api.cerebras.ai/v1/chat/completions"
    ):
        self.api_key = api_key or os.getenv("CEREBRAS_API_KEY")
        if not self.api_key:
            raise ValueError("CEREBRAS_API_KEY not provided")

        self.model = model
        self.api_url = api_url
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def chat(
            self,
            messages: List[Dict[str, str]],
            temperature: float = 1.0,
            **kwargs
    ) -> str:
        """Send chat completion request"""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            **kwargs
        }

        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()

            result = response.json()
            return result["choices"][0]["message"]["content"]

        except requests.exceptions.RequestException as e:
            logger.error(f"Cerebras API error: {e}")
            raise

    def complete(
            self,
            prompt: str,
            system_prompt: Optional[str] = None,
            **kwargs
    ) -> str:
        """Simple completion with optional system prompt"""
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        return self.chat(messages, **kwargs)
