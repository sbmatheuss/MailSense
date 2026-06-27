from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field

import anthropic
from django.conf import settings

logger = logging.getLogger(__name__)

CLASSIFICATION_MODEL = "claude-sonnet-4-6"
MAX_TOKENS_SINGLE = 1024
MAX_TOKENS_BATCH = 4096
BODY_TRUNCATION_CHARS = 2000

_SINGLE_SYSTEM = """\
You are an intelligent email classifier for a business inbox.

Analyze the provided email and return ONLY a valid JSON object with these exact fields:

{
  "category": "<one of: support, billing, bug, feature, sales, internal, newsletter, spam, other>",
  "priority": "<one of: critical, high, medium, low>",
  "sentiment": "<one of: positive, neutral, negative, urgent>",
  "confidence": <number between 0.0 and 1.0>,
  "summary": "<1-2 sentence summary of what the email is about>",
  "key_topics": ["<topic 1>", "<topic 2>"],
  "suggested_reply": "<professional reply if action needed, empty string otherwise>",
  "urgency_reason": "<reason this is urgent if critical/high priority, empty string otherwise>",
  "requires_action": <true or false>
}

Priority guidelines:
- critical: requires immediate response (legal, security, angry customer threatening churn, production down)
- high: needs response within 24 hours (billing issues, bugs affecting users, sales opportunities)
- medium: needs response within 1-3 days (feature requests, general support)
- low: informational or no response needed (newsletters, receipts, automated notifications)

Return ONLY the JSON object. No markdown, no explanation, no additional text."""

_BATCH_SYSTEM = """\
You are an intelligent email classifier for a business inbox.

Classify each email below and return ONLY a valid JSON array. \
The array must have exactly the same number of elements as emails, in the same order.

Each element schema:
{
  "category": "<one of: support, billing, bug, feature, sales, internal, newsletter, spam, other>",
  "priority": "<one of: critical, high, medium, low>",
  "sentiment": "<one of: positive, neutral, negative, urgent>",
  "confidence": <number between 0.0 and 1.0>,
  "summary": "<1-2 sentence summary>",
  "key_topics": ["<topic 1>", "<topic 2>"],
  "suggested_reply": "<professional reply if action needed, empty string otherwise>",
  "urgency_reason": "<reason this is urgent if critical/high priority, empty string otherwise>",
  "requires_action": <true or false>
}

Priority guidelines:
- critical: immediate response required (legal, security, production down, churn threat)
- high: response needed within 24h (billing, user-impacting bugs, sales)
- medium: response within 1-3 days (feature requests, general support)
- low: informational, no response needed (newsletters, receipts, notifications)

Return ONLY the JSON array. No markdown, no explanation, no additional text."""


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
    processing_time_ms: int = 0


class BatchParseError(Exception):
    """Raised when the batch LLM response cannot be parsed as a valid JSON array."""


class LLMService:
    """Wrapper da Anthropic API com retry, fallback e métricas."""

    def __init__(self) -> None:
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = CLASSIFICATION_MODEL
        self.max_retries = 3

    def classify_email(self, subject: str, body: str, context: dict | None = None) -> ClassificationResult:
        """Classifica um único e-mail."""
        user_prompt = self._build_single_prompt(subject, body)
        start = time.monotonic()

        message = self.client.messages.create(
            model=self.model,
            max_tokens=MAX_TOKENS_SINGLE,
            temperature=0,
            system=_SINGLE_SYSTEM,
            messages=[{"role": "user", "content": user_prompt}],
        )

        elapsed_ms = int((time.monotonic() - start) * 1000)
        logger.info(
            "classify_email tokens: input=%d output=%d elapsed_ms=%d",
            message.usage.input_tokens,
            message.usage.output_tokens,
            elapsed_ms,
        )

        result = self._parse_single_response(message.content[0].text)
        result.processing_time_ms = elapsed_ms
        return result

    def classify_batch(self, emails: list[dict], batch_size: int = 5) -> list[ClassificationResult]:
        """Classifica um lote de e-mails em uma única chamada.

        Raises BatchParseError if the response JSON cannot be parsed — callers
        should catch this and fall back to individual classification.
        """
        results: list[ClassificationResult] = []
        for i in range(0, len(emails), batch_size):
            chunk = emails[i : i + batch_size]
            results.extend(self._classify_chunk(chunk))
        return results

    def generate_reply(self, email: dict, classification: dict, tone: str = "professional") -> str:
        """Gera sugestão de resposta baseada no contexto."""
        subject = email.get("subject", "")
        body = email.get("body_text", "")[:BODY_TRUNCATION_CHARS]
        category = classification.get("category", "other")
        priority = classification.get("priority", "medium")

        prompt = (
            f"Email subject: {subject}\n"
            f"Email body:\n{body}\n\n"
            f"Category: {category}, Priority: {priority}\n\n"
            f"Write a {tone} reply to this email. "
            "Return only the reply body text — no subject line, no signature placeholder."
        )

        message = self.client.messages.create(
            model=self.model,
            max_tokens=512,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )

        logger.info(
            "generate_reply tokens: input=%d output=%d",
            message.usage.input_tokens,
            message.usage.output_tokens,
        )
        return message.content[0].text.strip()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _classify_chunk(self, emails: list[dict]) -> list[ClassificationResult]:
        user_prompt = self._build_batch_prompt(emails)
        max_tokens = min(MAX_TOKENS_SINGLE * len(emails), MAX_TOKENS_BATCH)

        start = time.monotonic()
        message = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=0,
            system=_BATCH_SYSTEM,
            messages=[{"role": "user", "content": user_prompt}],
        )
        elapsed_ms = int((time.monotonic() - start) * 1000)

        logger.info(
            "classify_batch chunk_size=%d tokens: input=%d output=%d elapsed_ms=%d",
            len(emails),
            message.usage.input_tokens,
            message.usage.output_tokens,
            elapsed_ms,
        )

        per_email_ms = elapsed_ms // len(emails)
        results = self._parse_batch_response(message.content[0].text, expected_count=len(emails))
        for r in results:
            r.processing_time_ms = per_email_ms
        return results

    def _build_single_prompt(self, subject: str, body: str) -> str:
        return f"Subject: {subject}\n\nBody:\n{body[:BODY_TRUNCATION_CHARS]}"

    def _build_batch_prompt(self, emails: list[dict]) -> str:
        parts = []
        for i, email in enumerate(emails, start=1):
            body = email.get("body_text", "")[:BODY_TRUNCATION_CHARS]
            parts.append(
                f"--- Email {i} ---\n"
                f"Subject: {email.get('subject', '')}\n"
                f"Body:\n{body}"
            )
        return "\n\n".join(parts)

    def _parse_single_response(self, raw: str) -> ClassificationResult:
        try:
            data = json.loads(raw.strip())
        except json.JSONDecodeError as exc:
            raise BatchParseError(f"Single response JSON parse failed: {exc}") from exc
        return self._dict_to_result(data)

    def _parse_batch_response(self, raw: str, expected_count: int) -> list[ClassificationResult]:
        try:
            data = json.loads(raw.strip())
        except json.JSONDecodeError as exc:
            raise BatchParseError(f"Batch response JSON parse failed: {exc}") from exc

        if not isinstance(data, list):
            raise BatchParseError(f"Expected JSON array, got {type(data).__name__}")

        if len(data) != expected_count:
            raise BatchParseError(f"Expected {expected_count} results, got {len(data)}")

        return [self._dict_to_result(item) for item in data]

    def _dict_to_result(self, data: dict) -> ClassificationResult:
        return ClassificationResult(
            category=str(data.get("category", "other")),
            priority=str(data.get("priority", "medium")),
            sentiment=str(data.get("sentiment", "neutral")),
            confidence=float(data.get("confidence", 0.5)),
            summary=str(data.get("summary", "")),
            key_topics=list(data.get("key_topics", [])),
            suggested_reply=str(data.get("suggested_reply", "")),
            urgency_reason=str(data.get("urgency_reason", "")),
            requires_action=bool(data.get("requires_action", False)),
        )
