from __future__ import annotations

from dataclasses import dataclass

import anthropic
from django.conf import settings


@dataclass
class ClassificationResult:
    category: str
    priority: str
    sentiment: str
    confidence: float
    summary: str
    key_topics: list[str]
    suggested_reply: str
    urgency_reason: str
    requires_action: bool


class LLMService:
    """Wrapper da Anthropic API com retry, fallback e métricas."""

    def __init__(self) -> None:
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-6"
        self.max_retries = 3

    def classify_email(self, subject: str, body: str, context: dict | None = None) -> ClassificationResult:
        """Classifica um único e-mail."""
        raise NotImplementedError

    def classify_batch(self, emails: list[dict], batch_size: int = 5) -> list[ClassificationResult]:
        """Classifica um lote de e-mails em uma única chamada."""
        raise NotImplementedError

    def generate_reply(self, email: dict, classification: dict, tone: str = "professional") -> str:
        """Gera sugestão de resposta baseada no contexto."""
        raise NotImplementedError
