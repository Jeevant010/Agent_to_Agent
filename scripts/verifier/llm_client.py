#!/usr/bin/env python3
"""
scripts/llm_client.py

Lightweight, multi-provider HTTP client supporting:
  - Groq API (via OpenAI-compatible endpoint with Cloudflare-safe headers)
  - OpenAI-compatible endpoints (vLLM, LocalAI, OpenAI)
  - Local Ollama instances
"""

import os
import json
import logging
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional

logger = logging.getLogger("aavs.llm_client")


def load_env_file(env_path: Optional[Path] = None) -> None:
    """Loads key=value pairs from a .env file into os.environ if not already present."""
    candidate_paths = [
        env_path,
        Path(__file__).parent.parent / ".env",
        Path(".env")
    ]
    for p in candidate_paths:
        if p and p.is_file():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        key, val = line.split("=", 1)
                        key = key.strip()
                        val = val.strip().strip("'\"")
                        if key and key not in os.environ:
                            os.environ[key] = val
                break
            except Exception:
                pass


class LLMClient:
    """HTTP client supporting Groq, OpenAI-compatible APIs, and local Ollama."""

    def __init__(
        self,
        provider: str = "auto",
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        load_env_file()

        groq_key = api_key or os.getenv("GROQ_KEY")
        openai_key = api_key or os.getenv("OPENAI_API_KEY")

        if provider == "auto":
            if groq_key:
                self.provider = "groq"
                self.api_key = groq_key
                self.base_url = base_url or os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
                self.model = model or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
            elif openai_key:
                self.provider = "openai"
                self.api_key = openai_key
                self.base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
                self.model = model or "gpt-4o-mini"
            else:
                self.provider = "ollama"
                self.api_key = None
                self.base_url = None
                self.model = model or os.getenv("OLLAMA_MODEL", "mistral-nemo:latest")
        elif provider == "groq":
            self.provider = "groq"
            self.api_key = groq_key
            self.base_url = base_url or os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
            self.model = model or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        elif provider == "openai":
            self.provider = "openai"
            self.api_key = openai_key
            self.base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
            self.model = model or "gpt-4o-mini"
        else:
            self.provider = provider
            self.api_key = None
            self.base_url = None
            self.model = model or os.getenv("OLLAMA_MODEL", "mistral-nemo:latest")

        self.ollama_url = os.getenv("OLLAMA_HOST", "http://localhost:11434")

    def generate(self, prompt: str) -> str:
        """Dispatches prompt to the configured provider (Groq, OpenAI, or local Ollama)."""
        if self.provider in ("groq", "openai") and self.api_key:
            return self._call_openai_compatible(prompt)
        elif self.provider in ("ollama", "auto"):
            try:
                return self._call_ollama(prompt)
            except Exception:
                raise RuntimeError(
                    f"No LLM backend available. Neither a valid GROQ_KEY / OPENAI_API_KEY was provided nor was "
                    f"Ollama reachable at {self.ollama_url}. Please configure GROQ_KEY in .env or start Ollama (`ollama run {self.model}`)."
                )
        raise RuntimeError("No LLM backend configured. Set GROQ_KEY in .env or start local Ollama.")

    def _call_openai_compatible(self, prompt: str) -> str:
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        payload = json.dumps({
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a precise software test synthesis agent. You output only executable Python pytest code."
                },
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 800
        }).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                choices = data.get("choices", [])
                if not choices:
                    return ""
                message = choices[0].get("message", {})
                content = message.get("content") or ""
                reasoning = message.get("reasoning_content") or message.get("reasoning") or ""
                if not content.strip() and reasoning.strip():
                    content = reasoning
                return content
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"{self.provider.upper()} API error (HTTP {e.code}): {err_body}")

    def _call_ollama(self, prompt: str) -> str:
        url = f"{self.ollama_url.rstrip('/')}/api/generate"
        payload = json.dumps({
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1}
        }).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("response", "")
