"""llm.providers — one chat() signature, two backends.

The Meta backend talks to the Meta Model API. The mock backend never touches the
network, so CI, judges and the offline demo can run the whole pipeline with no key.

The contract every provider honours:

    chat(prompt, system=..., json_mode=...) -> str      # the raw text
    chat_json(prompt, ..., retries=3) -> dict           # parsed JSON, retried

`chat_json` is where the retry loop lives: a malformed reply is fed back to the
model together with the parse error, up to `retries` times, and then the caller
falls back to the local parser.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Optional

DEFAULT_MODEL = "muse-spark-1.3"
DEFAULT_BASE_URL = "https://modelapi.meta.com/llama/v1"


class ProviderError(RuntimeError):
    """Raised when a provider cannot produce an answer."""


def _strip_fences(text: str) -> str:
    """Pull the JSON out of a fenced block, if the model wrapped it in one."""
    s = text.strip()
    if s.startswith("```"):
        s = s.split("```", 2)[1] if s.count("```") >= 2 else s
        if s.lstrip().lower().startswith("json"):
            s = s.lstrip()[4:]
    return s.strip()


@dataclass
class Provider:
    """Base provider. Subclasses implement `chat`."""

    name: str = "base"
    model: str = DEFAULT_MODEL
    calls: list = field(default_factory=list)   # prompts seen, for tests and logs

    def chat(self, prompt: str, *, system: str = "", model: Optional[str] = None,
             temperature: float = 0.0, max_tokens: Optional[int] = None,
             json_mode: bool = False) -> str:
        raise NotImplementedError

    def chat_json(self, prompt: str, *, system: str = "", model: Optional[str] = None,
                  retries: int = 3, validate=None) -> dict:
        """Return parsed JSON, retrying with the error fed back to the model.

        `validate` is an optional callable: if it returns a list of problems, they
        are fed back to the model the same way a parse error is.
        """
        last_error: Optional[str] = None
        for attempt in range(retries + 1):
            text = self.chat(prompt, system=system, model=model, json_mode=True)
            try:
                data = json.loads(_strip_fences(text))
            except json.JSONDecodeError as exc:
                last_error = str(exc)
                feedback = f"not valid JSON ({exc})"
            else:
                if validate is None:
                    return data
                problems = validate(data)
                if not problems:
                    return data
                last_error = "; ".join(problems)
                feedback = ("failed schema validation:\n"
                            + "\n".join(f"- {p}" for p in problems))
            if attempt < retries:
                prompt = (
                    f"{prompt}\n\nYour previous reply was {feedback}. "
                    f"Reply with a single valid JSON object and nothing else."
                )
        raise ProviderError(
            f"{self.name}: no valid JSON after {retries} retries ({last_error})")


class MetaProvider(Provider):
    """The Meta Model API. OpenAI-compatible chat completions."""

    name = "meta"

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None,
                 model: Optional[str] = None, timeout: float = 60.0):
        self.api_key = api_key or os.environ.get("META_API_KEY", "")
        self.base_url = (base_url or os.environ.get("META_API_BASE_URL")
                         or DEFAULT_BASE_URL).rstrip("/")
        super().__init__(model=model or os.environ.get("META_MODEL", DEFAULT_MODEL))
        self.timeout = timeout
        if not self.api_key:
            raise ProviderError(
                "META_API_KEY is not set. Claim the Meta Model API credits, or run "
                "with MODEL_PROVIDER=mock.")

    def chat(self, prompt: str, *, system: str = "", model: Optional[str] = None,
             temperature: float = 0.0, max_tokens: Optional[int] = None,
             json_mode: bool = False) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        body: dict[str, Any] = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens:
            body["max_tokens"] = max_tokens
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        self.calls.append(prompt)
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self.api_key}"},
            method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:400]
            raise ProviderError(f"meta: HTTP {exc.code} — {detail}") from exc
        except urllib.error.URLError as exc:
            raise ProviderError(f"meta: cannot reach the API ({exc.reason})") from exc
        try:
            return payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise ProviderError(f"meta: unexpected response shape: {body_keys(payload)}") from exc


def body_keys(payload: dict) -> list:
    try:
        return sorted(payload.keys())
    except Exception:                                   # pragma: no cover
        return []


class MockProvider(Provider):
    """Offline backend. Returns a deterministic fixture; never touches the network.

    The mock is what CI runs and what the demo runs when no key is present, so the
    refusal path is always demonstrable.
    """

    name = "mock"

    def __init__(self, model: str = "mock", fixture: Optional[dict] = None):
        super().__init__(model=model)
        self.fixture = fixture

    def chat(self, prompt: str, *, system: str = "", model: Optional[str] = None,
             temperature: float = 0.0, max_tokens: Optional[int] = None,
             json_mode: bool = False) -> str:
        self.calls.append(prompt)
        if self.fixture is not None:
            return json.dumps(self.fixture)
        return json.dumps({"goal": "offline mock reply", "peripherals": []})


def get_provider(name: Optional[str] = None, **kwargs) -> Provider:
    """Build the configured provider. Defaults to MODEL_PROVIDER, then `mock`."""
    name = (name or os.environ.get("MODEL_PROVIDER") or "mock").strip().lower()
    if name == "meta":
        return MetaProvider(**kwargs)
    if name == "mock":
        return MockProvider(**kwargs)
    raise ProviderError(f"unknown provider: {name!r} (expected 'meta' or 'mock')")
