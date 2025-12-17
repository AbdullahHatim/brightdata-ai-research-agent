from __future__ import annotations

import os
from typing import Any, Dict, List, Literal, Optional

import requests
from tenacity import retry, stop_after_attempt, wait_exponential


Provider = Literal["openai_compatible", "ollama", "google", "none"]


class LLMError(RuntimeError):
    pass


class LLM:
    def __init__(
        self,
        provider: Provider = "openai_compatible",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_s: int = 60,
    ) -> None:
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.timeout_s = timeout_s

    @staticmethod
    def from_env() -> "LLM":
        provider = os.getenv("LLM_PROVIDER", "openai_compatible").strip().lower()
        if provider == "none":
            return LLM(provider="none")

        if provider == "ollama":
            return LLM(
                provider="ollama",
                model=os.getenv("OLLAMA_MODEL", "llama3.1"),
                base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                timeout_s=int(os.getenv("LLM_TIMEOUT_S", "120")),
            )

        if provider == "google":
            return LLM(
                provider="google",
                model=os.getenv("GOOGLE_MODEL", "gemini-3-flash-preview"),
                api_key=os.getenv("GOOGLE_API_KEY"),
                timeout_s=int(os.getenv("LLM_TIMEOUT_S", "60")),
            )

        # default: OpenAI-compatible Chat Completions
        return LLM(
            provider="openai_compatible",
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            timeout_s=int(os.getenv("LLM_TIMEOUT_S", "60")),
        )

    @retry(wait=wait_exponential(min=1, max=20), stop=stop_after_attempt(3))
    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.2) -> str:
        if self.provider == "none":
            raise LLMError("LLM provider is 'none'.")

        if self.provider == "ollama":
            return self._chat_ollama(messages=messages, temperature=temperature)

        if self.provider == "openai_compatible":
            return self._chat_openai_compatible(messages=messages, temperature=temperature)

        if self.provider == "google":
            return self._chat_google(messages=messages, temperature=temperature)

        raise LLMError(f"Unknown provider: {self.provider}")

    def _chat_openai_compatible(self, messages: List[Dict[str, str]], temperature: float) -> str:
        if not self.api_key:
            raise LLMError("Missing OPENAI_API_KEY (set it in .env).")
        if not self.base_url or not self.model:
            raise LLMError("Missing OPENAI_BASE_URL/OPENAI_MODEL.")

        url = self.base_url.rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }

        r = requests.post(url, headers=headers, json=payload, timeout=self.timeout_s)
        if r.status_code >= 400:
            raise LLMError(f"OpenAI-compatible error {r.status_code}: {r.text[:500]}")
        data = r.json()
        try:
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            raise LLMError(f"Unexpected OpenAI-compatible response: {data}") from e

    def _chat_ollama(self, messages: List[Dict[str, str]], temperature: float) -> str:
        if not self.base_url or not self.model:
            raise LLMError("Missing OLLAMA_BASE_URL/OLLAMA_MODEL.")

        url = self.base_url.rstrip("/") + "/api/chat"
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }

        r = requests.post(url, json=payload, timeout=self.timeout_s)
        if r.status_code >= 400:
            raise LLMError(f"Ollama error {r.status_code}: {r.text[:500]}")
        data = r.json()
        if "message" in data and "content" in data["message"]:
            return data["message"]["content"]
        raise LLMError(f"Unexpected Ollama response: {data}")

    def _chat_google(self, messages: List[Dict[str, str]], temperature: float) -> str:
        if not self.api_key:
            raise LLMError("Missing GOOGLE_API_KEY (set it in .env).")
        if not self.model:
            raise LLMError("Missing GOOGLE_MODEL.")

        # Gemini REST API
        # https://ai.google.dev/api/rest/v1beta/models/generateContent
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        
        # Convert OpenAI-style messages to Gemini contents
        # OpenAI: [{"role": "user", "content": "hello"}, {"role": "system", "content": "..."}]
        # Gemini: contents=[{"parts": [{"text": "..."}], "role": "user"}]
        # Note: Gemini 'system' instructions are often passed differently or just as user/model turns.
        # For simplicity in this agent, we'll map 'system' -> 'user' or prepend it, 
        # but Gemini 1.5+ supports system_instruction. Let's use simple mapping for now to match the list structure.
        
        gemini_contents = []
        system_instruction = None
        
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            
            if role == "system":
                # Save system prompt to pass as system_instruction (supported in v1beta)
                # If there are multiple system messages, we'll concatenate them.
                if system_instruction is None:
                    system_instruction = {"parts": [{"text": content}]}
                else:
                    system_instruction["parts"][0]["text"] += "\n" + content
            elif role == "user":
                gemini_contents.append({"role": "user", "parts": [{"text": content}]})
            elif role == "assistant":
                gemini_contents.append({"role": "model", "parts": [{"text": content}]})
            else:
                # Fallback for other roles
                gemini_contents.append({"role": "user", "parts": [{"text": f"[{role}]: {content}"}]})

        payload: Dict[str, Any] = {
            "contents": gemini_contents,
            "generationConfig": {
                "temperature": temperature,
            },
        }

        if system_instruction:
            payload["system_instruction"] = system_instruction

        r = requests.post(url, json=payload, timeout=self.timeout_s)
        if r.status_code >= 400:
            raise LLMError(f"Google Gemini error {r.status_code}: {r.text[:500]}")
        
        data = r.json()
        # Response: {"candidates": [{"content": {"parts": [{"text": "..."}]}, ...}]}
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            # Check for safety ratings blocks
            if "promptFeedback" in data:
                raise LLMError(f"Gemini prompt feedback: {data['promptFeedback']}") from e
            raise LLMError(f"Unexpected Gemini response: {data}") from e
