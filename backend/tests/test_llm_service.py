"""Unit tests for LLMService — all Anthropic API calls are mocked."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from services.llm_service import (
    BODY_TRUNCATION_CHARS,
    BatchParseError,
    ClassificationResult,
    LLMService,
)

# ── Fixtures & helpers ─────────────────────────────────────────────────────

VALID_ITEM = {
    "category": "support",
    "priority": "high",
    "sentiment": "negative",
    "confidence": 0.92,
    "summary": "User cannot access the dashboard.",
    "key_topics": ["access", "dashboard"],
    "suggested_reply": "We are investigating.",
    "urgency_reason": "Customer is blocked.",
    "requires_action": True,
}


def _mock_message(text: str, input_tokens: int = 100, output_tokens: int = 50) -> MagicMock:
    msg = MagicMock()
    msg.content = [MagicMock(text=text)]
    msg.usage.input_tokens = input_tokens
    msg.usage.output_tokens = output_tokens
    return msg


@pytest.fixture()
def mock_client(settings):
    settings.ANTHROPIC_API_KEY = "test-key"
    with patch("services.llm_service.anthropic.Anthropic") as mock_cls:
        client = MagicMock()
        mock_cls.return_value = client
        yield client


# ── ClassificationResult defaults ─────────────────────────────────────────


class TestDictToResult:
    def test_full_payload_maps_all_fields(self, mock_client):
        mock_client.messages.create.return_value = _mock_message(json.dumps(VALID_ITEM))
        result = LLMService().classify_email("S", "B")

        assert result.category == "support"
        assert result.priority == "high"
        assert result.sentiment == "negative"
        assert result.confidence == 0.92
        assert result.requires_action is True
        assert result.key_topics == ["access", "dashboard"]

    def test_missing_fields_use_safe_defaults(self, mock_client):
        mock_client.messages.create.return_value = _mock_message(json.dumps({"category": "bug"}))
        result = LLMService().classify_email("S", "B")

        assert result.priority == "medium"
        assert result.sentiment == "neutral"
        assert result.confidence == 0.5
        assert result.key_topics == []
        assert result.requires_action is False
        assert result.suggested_reply == ""


# ── classify_email ─────────────────────────────────────────────────────────


class TestClassifyEmail:
    def test_returns_classification_result_type(self, mock_client):
        mock_client.messages.create.return_value = _mock_message(json.dumps(VALID_ITEM))
        result = LLMService().classify_email("Subject", "Body")
        assert isinstance(result, ClassificationResult)

    def test_calls_api_with_temperature_zero(self, mock_client):
        mock_client.messages.create.return_value = _mock_message(json.dumps(VALID_ITEM))
        LLMService().classify_email("Subject", "Body")
        kwargs = mock_client.messages.create.call_args.kwargs
        assert kwargs["temperature"] == 0

    def test_truncates_body_at_2000_chars(self, mock_client):
        mock_client.messages.create.return_value = _mock_message(json.dumps(VALID_ITEM))
        long_body = "x" * 5000
        LLMService().classify_email("Subject", long_body)
        kwargs = mock_client.messages.create.call_args.kwargs
        user_content: str = kwargs["messages"][0]["content"]
        assert "x" * 2000 in user_content
        assert "x" * 2001 not in user_content

    def test_sets_processing_time_ms(self, mock_client):
        mock_client.messages.create.return_value = _mock_message(json.dumps(VALID_ITEM))
        result = LLMService().classify_email("Subject", "Body")
        assert result.processing_time_ms >= 0

    def test_raises_batch_parse_error_on_invalid_json(self, mock_client):
        mock_client.messages.create.return_value = _mock_message("not valid JSON at all")
        with pytest.raises(BatchParseError):
            LLMService().classify_email("Subject", "Body")

    def test_uses_single_system_prompt(self, mock_client):
        mock_client.messages.create.return_value = _mock_message(json.dumps(VALID_ITEM))
        LLMService().classify_email("Subject", "Body")
        kwargs = mock_client.messages.create.call_args.kwargs
        # Single classification prompt contains "single" schema instructions
        assert "category" in kwargs["system"]
        assert isinstance(kwargs["system"], str)


# ── classify_batch ─────────────────────────────────────────────────────────


class TestClassifyBatch:
    def test_returns_list_of_results(self, mock_client):
        two_items = [VALID_ITEM, {**VALID_ITEM, "category": "billing"}]
        mock_client.messages.create.return_value = _mock_message(json.dumps(two_items))
        emails = [{"id": i, "subject": f"S{i}", "body_text": f"B{i}"} for i in range(2)]
        results = LLMService().classify_batch(emails, batch_size=5)
        assert len(results) == 2
        assert results[0].category == "support"
        assert results[1].category == "billing"

    def test_raises_batch_parse_error_on_invalid_json(self, mock_client):
        mock_client.messages.create.return_value = _mock_message("this is not JSON")
        with pytest.raises(BatchParseError):
            LLMService().classify_batch([{"id": 1, "subject": "S", "body_text": "B"}])

    def test_raises_batch_parse_error_when_count_mismatch(self, mock_client):
        mock_client.messages.create.return_value = _mock_message(json.dumps([VALID_ITEM]))
        emails = [{"id": i, "subject": f"S{i}", "body_text": f"B{i}"} for i in range(2)]
        with pytest.raises(BatchParseError, match="Expected 2 results, got 1"):
            LLMService().classify_batch(emails, batch_size=5)

    def test_raises_batch_parse_error_when_not_array(self, mock_client):
        mock_client.messages.create.return_value = _mock_message(json.dumps(VALID_ITEM))
        with pytest.raises(BatchParseError, match="Expected JSON array"):
            LLMService().classify_batch([{"id": 1, "subject": "S", "body_text": "B"}])

    def test_max_tokens_scales_with_chunk_size(self, mock_client):
        three_items = [VALID_ITEM] * 3
        mock_client.messages.create.return_value = _mock_message(json.dumps(three_items))
        emails = [{"id": i, "subject": f"S{i}", "body_text": f"B{i}"} for i in range(3)]
        LLMService().classify_batch(emails, batch_size=5)
        kwargs = mock_client.messages.create.call_args.kwargs
        assert kwargs["max_tokens"] == 3 * 1024  # min(3*1024, 4096) = 3072

    def test_max_tokens_capped_at_4096(self, mock_client):
        five_items = [VALID_ITEM] * 5
        mock_client.messages.create.return_value = _mock_message(json.dumps(five_items))
        emails = [{"id": i, "subject": f"S{i}", "body_text": f"B{i}"} for i in range(5)]
        LLMService().classify_batch(emails, batch_size=5)
        kwargs = mock_client.messages.create.call_args.kwargs
        assert kwargs["max_tokens"] == 4096

    def test_splits_into_multiple_api_calls(self, mock_client):
        mock_client.messages.create.side_effect = [
            _mock_message(json.dumps([VALID_ITEM] * 5)),
            _mock_message(json.dumps([VALID_ITEM] * 2)),
        ]
        emails = [{"id": i, "subject": f"S{i}", "body_text": f"B{i}"} for i in range(7)]
        results = LLMService().classify_batch(emails, batch_size=5)
        assert len(results) == 7
        assert mock_client.messages.create.call_count == 2

    def test_sets_per_email_processing_time(self, mock_client):
        two_items = [VALID_ITEM, VALID_ITEM]
        mock_client.messages.create.return_value = _mock_message(json.dumps(two_items))
        emails = [{"id": i, "subject": f"S{i}", "body_text": f"B{i}"} for i in range(2)]
        results = LLMService().classify_batch(emails, batch_size=5)
        assert all(r.processing_time_ms >= 0 for r in results)


# ── generate_reply ─────────────────────────────────────────────────────────


class TestGenerateReply:
    def test_returns_stripped_string(self, mock_client):
        mock_client.messages.create.return_value = _mock_message("  Thank you for reaching out.  ")
        result = LLMService().generate_reply(
            {"subject": "Help needed", "body_text": "I need help"},
            {"category": "support", "priority": "high"},
        )
        assert result == "Thank you for reaching out."

    def test_truncates_body_in_prompt(self, mock_client):
        mock_client.messages.create.return_value = _mock_message("Reply text")
        LLMService().generate_reply(
            {"subject": "S", "body_text": "x" * 5000},
            {"category": "support", "priority": "medium"},
        )
        kwargs = mock_client.messages.create.call_args.kwargs
        content: str = kwargs["messages"][0]["content"]
        assert "x" * BODY_TRUNCATION_CHARS in content
        assert "x" * (BODY_TRUNCATION_CHARS + 1) not in content

    def test_includes_category_and_priority_in_prompt(self, mock_client):
        mock_client.messages.create.return_value = _mock_message("Reply")
        LLMService().generate_reply(
            {"subject": "Invoice question", "body_text": "Body"},
            {"category": "billing", "priority": "high"},
        )
        kwargs = mock_client.messages.create.call_args.kwargs
        content: str = kwargs["messages"][0]["content"]
        assert "billing" in content
        assert "high" in content
