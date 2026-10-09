"""Gemini image model engine (online). The per-card prompt is sent with the image."""
import io
import os
import urllib.request
from typing import Callable

import numpy as np
from PIL import Image

from ..settings import Settings
from .base import Engine, EngineError


_network_prepared = False


def use_system_network_settings() -> None:
    """Make HTTPS work on corporate networks.

    Trust the Windows certificate store (companies that inspect HTTPS install their
    own root certificate there) and use the system proxy, which httpx ignores.
    """
    global _network_prepared
    if _network_prepared:
        return
    _network_prepared = True
    try:
        import truststore

        truststore.inject_into_ssl()
    except Exception:  # fall back to the bundled certificates
        pass
    proxies = urllib.request.getproxies()  # reads the Windows registry settings
    for scheme in ("https", "http"):
        key = f"{scheme.upper()}_PROXY"
        if proxies.get(scheme) and not (os.environ.get(key) or os.environ.get(key.lower())):
            os.environ[key] = proxies[scheme]


def _default_client_factory(api_key: str):
    use_system_network_settings()
    from google import genai

    return genai.Client(api_key=api_key)


def _friendly_error(exc: Exception) -> str:
    code = getattr(exc, "code", None)
    message = str(getattr(exc, "message", "") or exc)
    if code in (401, 403) or "API key" in message:
        return "Gemini: the API key was rejected. Check it in Settings."
    if code == 404:
        return "Gemini: model not found. Pick another model in Settings."
    if code == 429:
        return "Gemini: rate limit or quota reached. Try again later."
    if code is not None and code >= 500:
        return "Gemini: the service had an error. Try again."
    if code is None:
        return f"Gemini: cannot reach Google's servers (network blocked or offline). {message[:120]}"
    return f"Gemini error {code}: {message[:200]}"


class GeminiEngine(Engine):
    id = "gemini"
    name = "Gemini (online)"
    online = True

    def __init__(self, settings_provider: Callable[[], Settings], client_factory=_default_client_factory):
        self._settings = settings_provider
        self._client_factory = client_factory

    def available(self):
        return bool(self._settings().gemini_api_key.strip())

    def unavailable_reason(self):
        return "add your Gemini API key in Settings"

    def run(self, rgb, variation=0, prompt=""):
        settings = self._settings()
        if not settings.gemini_api_key.strip():
            raise EngineError(f"Gemini: {self.unavailable_reason()}.")
        prompt = prompt.strip() or settings.default_prompt
        height, width = rgb.shape[:2]
        try:
            from google.genai import types

            client = self._client_factory(settings.gemini_api_key.strip())
            response = client.models.generate_content(
                model=settings.gemini_model,
                contents=[prompt, Image.fromarray(rgb)],
                config=types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"]),
            )
        except EngineError:
            raise
        except Exception as exc:  # SDK raises many types (APIError, httpx errors, ...)
            raise EngineError(_friendly_error(exc)) from exc
        data = _first_image_bytes(response)
        if data is None:
            text = _response_text(response)
            raise EngineError("Gemini returned no image." + (f" It said: {text[:200]}" if text else ""))
        image = Image.open(io.BytesIO(data)).convert("L")
        if image.size != (width, height):
            image = image.resize((width, height), Image.LANCZOS)
        return np.array(image)


def _parts(response):
    for candidate in getattr(response, "candidates", None) or []:
        content = getattr(candidate, "content", None)
        yield from getattr(content, "parts", None) or []


def _first_image_bytes(response):
    for part in _parts(response):
        inline = getattr(part, "inline_data", None)
        if inline is not None and getattr(inline, "data", None):
            return inline.data
    return None


def _response_text(response):
    return " ".join(p.text for p in _parts(response) if getattr(p, "text", None)).strip()
