import pytest
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.emails.models import Email, EmailClassification


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    u = User.objects.create_user(
        username="testuser", password="testpass123", email="test@example.com"
    )
    return u


@pytest.fixture
def other_user(db):
    u = User.objects.create_user(
        username="other", password="testpass123", email="other@example.com"
    )
    return u


@pytest.fixture
def auth_client(user):
    client = APIClient()
    token, _ = Token.objects.get_or_create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


@pytest.fixture
def other_client(other_user):
    client = APIClient()
    token, _ = Token.objects.get_or_create(user=other_user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


# ── Helpers (not fixtures) ─────────────────────────────────────────────────

_email_counter = 0


def make_email(user: User, **kwargs) -> Email:
    global _email_counter
    _email_counter += 1
    defaults = dict(
        gmail_id=f"test_{user.pk}_{_email_counter}",
        thread_id=f"thread_{_email_counter}",
        from_address="sender@example.com",
        from_name="Test Sender",
        to_address=[user.email],
        cc_address=[],
        subject="Test Subject",
        body_text="Test body text.",
        body_html="",
        received_at=timezone.now(),
        status=Email.Status.PENDING,
        is_read=False,
        is_archived=False,
        has_attachments=False,
        raw_headers={},
    )
    defaults.update(kwargs)
    return Email.objects.create(user=user, **defaults)


def make_classification(email: Email, **kwargs) -> EmailClassification:
    defaults = dict(
        category="support",
        priority="medium",
        sentiment="neutral",
        confidence_score=0.85,
        summary="Test summary.",
        key_topics=["test"],
        suggested_reply="",
        urgency_reason="",
        requires_action=False,
        user_corrected=False,
        original_category="",
        original_priority="",
        original_sentiment="",
        processing_time_ms=1000,
    )
    defaults.update(kwargs)
    return EmailClassification.objects.create(email=email, **defaults)
