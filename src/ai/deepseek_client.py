import logging
import os
import time
from typing import Optional

import requests

from src.utils.json_utils import extract_first_json_object


class DeepSeekClient:
    def __init__(self, config: Optional[dict] = None):
        cfg = config or {}
        self.api_key_env = cfg.get("api_key_env", "DEEPSEEK_API_KEY")
        self.api_key = os.getenv(self.api_key_env, "")
        self.base_url = cfg.get("base_url", "https://api.deepseek.com/v1").rstrip("/")
        self.model = cfg.get("model", "deepseek-v4-flash")
        self.timeout = int(cfg.get("timeout_seconds", 60))
        self.max_retries = int(cfg.get("max_retries", 2))
        self.enabled = bool(cfg.get("enabled", True))

    def is_available(self) -> bool:
        return self.enabled and bool(self.api_key)

    def chat_json(self, system_prompt: str, user_prompt: str) -> Optional[dict]:
        if not self.is_available():
            return None
        url = f"{self.base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        for attempt in range(self.max_retries + 1):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                return extract_first_json_object(content)
            except Exception as exc:
                logging.warning("DeepSeek 调用失败 attempt=%s error=%s", attempt + 1, exc)
                if attempt < self.max_retries:
                    time.sleep(1 + attempt)
        return None
