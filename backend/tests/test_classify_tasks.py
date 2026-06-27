"""Tests for Celery classification tasks.

The LLMService is always mocked to keep these tests fast and self-contained.
`select_for_update(skip_locked=True)` requires PostgreSQL — run via `make test-back`.
"""

from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest
from celery.exceptions import Retry
from django.utils import timezone

from apps.emails.models import Email, EmailClassification
from services.llm_service import BatchParseError, ClassificationResult
from tests.conftest import make_email, make_classification


def _result(**kwargs) -> ClassificationResult:
    defaults = dict(
        category="support",
        priority="medium",
        sentiment="neutral",
        confidence=0.90,
        summary="Automated test summary.",
        key_topics=["test"],
        suggested_reply="Thank you.",
        urgency_reason="",
        requires_action=False,
        processing_time_ms=800,
    )
    defaults.update(kwargs)
    return ClassificationResult(**defaults)


# ── classify_email_task ────────────────────────────────────────────────────


@pytest.mark.django_db
class TestClassifyEmailTask:
    @patch("tasks.classify.LLMService")
    def test_classifies_and_sets_status_to_classified(self, MockLLM, user):
        from tasks.classify import classify_email_task

        email = make_email(user)
        MockLLM.return_value.classify_email.return_value = _result()

        classify_email_task(email.pk)

        email.refresh_from_db()
        assert email.status == Email.Status.CLASSIFIED

    @patch("tasks.classify.LLMService")
    def test_persists_classification_record(self, MockLLM, user):
        from tasks.classify import classify_email_task

        email = make_email(user)
        MockLLM.return_value.classify_email.return_value = _result(
            category="billing", priority="high"
        )

        classify_email_task(email.pk)

        clf = EmailClassification.objects.get(email=email)
        assert clf.category == "billing"
        assert clf.priority == "high"

    def test_skips_already_classified_email(self, user):
        from tasks.classify import classify_email_task

        email = make_email(user, status=Email.Status.CLASSIFIED)
        with patch("tasks.classify.LLMService") as MockLLM:
            classify_email_task(email.pk)
            MockLLM.return_value.classify_email.assert_not_called()

    def test_skips_nonexistent_email_without_raising(self):
        from tasks.classify import classify_email_task

        with patch("tasks.classify.LLMService") as MockLLM:
            classify_email_task(99999)
            MockLLM.return_value.classify_email.assert_not_called()

    @patch("tasks.classify.LLMService")
    def test_raises_retry_on_api_error(self, MockLLM, user):
        from tasks.classify import classify_email_task

        email = make_email(user)
        MockLLM.return_value.classify_email.side_effect = Exception("API timeout")

        with pytest.raises(Retry):
            classify_email_task(email.pk)

    @patch("tasks.classify.LLMService")
    def test_resets_to_pending_before_retry(self, MockLLM, user):
        from tasks.classify import classify_email_task

        email = make_email(user)
        MockLLM.return_value.classify_email.side_effect = Exception("Network error")

        with pytest.raises(Retry):
            classify_email_task(email.pk)

        email.refresh_from_db()
        assert email.status == Email.Status.PENDING

    @patch("tasks.classify.LLMService")
    def test_marks_failed_when_retries_exhausted(self, MockLLM, user):
        from tasks.classify import classify_email_task

        email = make_email(user)
        MockLLM.return_value.classify_email.side_effect = Exception("Persistent error")

        # Simulate exhausted retries by patching the task's request context
        original_run = classify_email_task.run
        task_instance = classify_email_task
        original_request = type(task_instance).request

        mock_request = MagicMock()
        mock_request.retries = task_instance.max_retries  # retries == max_retries → FAILED

        with patch.object(type(task_instance), "request", property(lambda self: mock_request)):
            task_instance.run(email.pk)

        email.refresh_from_db()
        assert email.status == Email.Status.FAILED

    @patch("tasks.notifications.notify_critical_email")
    @patch("tasks.classify.LLMService")
    def test_notifies_for_critical_emails(self, MockLLM, mock_notify, user):
        from tasks.classify import classify_email_task

        email = make_email(user)
        MockLLM.return_value.classify_email.return_value = _result(priority="critical")

        classify_email_task(email.pk)

        mock_notify.delay.assert_called_once_with(email.pk)

    @patch("tasks.notifications.notify_critical_email")
    @patch("tasks.classify.LLMService")
    def test_does_not_notify_for_non_critical(self, MockLLM, mock_notify, user):
        from tasks.classify import classify_email_task

        email = make_email(user)
        MockLLM.return_value.classify_email.return_value = _result(priority="medium")

        classify_email_task(email.pk)

        mock_notify.delay.assert_not_called()


# ── classify_pending_batch ─────────────────────────────────────────────────


@pytest.mark.django_db
class TestClassifyPendingBatch:
    @patch("tasks.classify.LLMService")
    def test_does_nothing_when_no_pending_emails(self, MockLLM, user):
        from tasks.classify import classify_pending_batch

        classify_pending_batch()

        MockLLM.return_value.classify_batch.assert_not_called()
        assert EmailClassification.objects.count() == 0

    @patch("tasks.classify.LLMService")
    def test_marks_emails_classified_on_success(self, MockLLM, user):
        from tasks.classify import classify_pending_batch

        e1 = make_email(user)
        e2 = make_email(user)
        MockLLM.return_value.classify_batch.return_value = [_result(), _result(category="billing")]

        classify_pending_batch()

        e1.refresh_from_db()
        e2.refresh_from_db()
        assert e1.status == Email.Status.CLASSIFIED
        assert e2.status == Email.Status.CLASSIFIED

    @patch("tasks.classify.LLMService")
    def test_creates_classification_records_on_success(self, MockLLM, user):
        from tasks.classify import classify_pending_batch

        e1 = make_email(user)
        MockLLM.return_value.classify_batch.return_value = [_result(category="feature")]

        classify_pending_batch()

        assert EmailClassification.objects.filter(email=e1, category="feature").exists()

    @patch("tasks.classify.classify_email_task")
    @patch("tasks.classify.LLMService")
    def test_falls_back_to_individual_on_batch_parse_error(self, MockLLM, mock_individual, user):
        from tasks.classify import classify_pending_batch

        email = make_email(user)
        MockLLM.return_value.classify_batch.side_effect = BatchParseError("bad JSON")

        classify_pending_batch()

        mock_individual.delay.assert_called_once_with(email.pk)

    @patch("tasks.classify.classify_email_task")
    @patch("tasks.classify.LLMService")
    def test_fallback_dispatches_one_task_per_email(self, MockLLM, mock_individual, user):
        from tasks.classify import classify_pending_batch

        emails = [make_email(user) for _ in range(3)]
        MockLLM.return_value.classify_batch.side_effect = BatchParseError("bad JSON")

        classify_pending_batch()

        assert mock_individual.delay.call_count == 3
        dispatched_ids = {c.args[0] for c in mock_individual.delay.call_args_list}
        assert dispatched_ids == {e.pk for e in emails}

    @patch("tasks.classify.LLMService")
    def test_sets_status_to_processing_before_api_call(self, MockLLM, user):
        from tasks.classify import classify_pending_batch

        email = make_email(user)
        captured = {}

        def fake_classify_batch(emails_data, **kw):
            email.refresh_from_db()
            captured["status_during"] = email.status
            return [_result()]

        MockLLM.return_value.classify_batch = fake_classify_batch

        classify_pending_batch()

        assert captured["status_during"] == Email.Status.PROCESSING

    @patch("tasks.classify.LLMService")
    def test_requeues_to_pending_on_api_error(self, MockLLM, user):
        from tasks.classify import classify_pending_batch

        email = make_email(user)
        MockLLM.return_value.classify_batch.side_effect = RuntimeError("Rate limited")

        with pytest.raises(RuntimeError):
            classify_pending_batch()

        email.refresh_from_db()
        assert email.status == Email.Status.PENDING

    @patch("tasks.classify.LLMService")
    def test_processes_at_most_batch_size_emails(self, MockLLM, user):
        from tasks.classify import classify_pending_batch, BATCH_SIZE

        # Create more emails than the batch size
        emails = [make_email(user) for _ in range(BATCH_SIZE + 3)]
        MockLLM.return_value.classify_batch.return_value = [_result()] * BATCH_SIZE

        classify_pending_batch()

        classified = Email.objects.filter(user=user, status=Email.Status.CLASSIFIED).count()
        assert classified == BATCH_SIZE
