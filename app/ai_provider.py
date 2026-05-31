from dataclasses import asdict, dataclass
from typing import Optional
from urllib.parse import urlparse

from openai import OpenAI


SUPPORTED_AI_PROVIDERS = {"auto", "deepseek", "openai", "openai-compatible"}
AI_PROTOCOL = "openai-compatible-chat-completions"


@dataclass(frozen=True)
class ProviderStatus:
    provider: str
    detected_provider: str
    protocol: str
    base_url: str
    api_key_configured: bool
    model: str
    deep_model: str
    timeout_seconds: float
    max_tokens: int

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ModelConfig:
    provider: str
    detected_provider: str
    api_key: str
    base_url: str
    model: str
    deep_model: str
    timeout_seconds: float
    max_tokens: int

    def to_status(self) -> ProviderStatus:
        return ProviderStatus(
            provider=self.provider,
            detected_provider=self.detected_provider,
            protocol=AI_PROTOCOL,
            base_url=self.base_url,
            api_key_configured=bool(self.api_key),
            model=self.model,
            deep_model=self.deep_model,
            timeout_seconds=self.timeout_seconds,
            max_tokens=self.max_tokens,
        )


def detect_ai_provider(base_url: str) -> str:
    host = urlparse(base_url or "").netloc.lower()
    if "deepseek" in host:
        return "deepseek"
    if "openai.com" in host:
        return "openai"
    return "openai-compatible"


def resolve_ai_provider(configured_provider: str, base_url: str) -> tuple[str, str]:
    configured = (configured_provider or "auto").strip().lower()
    if configured not in SUPPORTED_AI_PROVIDERS:
        configured = "openai-compatible"

    detected = detect_ai_provider(base_url)
    if configured == "auto":
        return detected, detected
    return configured, detected


def build_model_config(settings, api_key: Optional[str] = None, api_base: Optional[str] = None) -> ModelConfig:
    base_url = api_base or settings.ai_api_base
    provider, detected_provider = resolve_ai_provider(settings.ai_provider, base_url)
    return ModelConfig(
        provider=provider,
        detected_provider=detected_provider,
        api_key=settings.ai_api_key if api_key is None else api_key,
        base_url=base_url,
        model=settings.ai_model,
        deep_model=settings.ai_deep_model,
        timeout_seconds=settings.ai_timeout_seconds,
        max_tokens=settings.ai_max_tokens,
    )


class OpenAICompatibleAdapter:
    """Adapter for providers implementing OpenAI-compatible chat completions."""

    def __init__(self, config: ModelConfig, sdk_client=None):
        self.config = config
        self.client = sdk_client
        if self.client is None and config.api_key:
            self.client = OpenAI(
                api_key=config.api_key,
                base_url=config.base_url,
                timeout=config.timeout_seconds,
            )

    @property
    def enabled(self) -> bool:
        return self.client is not None

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.1,
    ) -> str:
        if not self.client:
            return ""
        try:
            resp = self.client.chat.completions.create(
                model=model or self.config.model,
                temperature=temperature,
                max_tokens=self.config.max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return resp.choices[0].message.content or ""
        except Exception:
            return ""
