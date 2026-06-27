"""Integration tests for email and dashboard API endpoints."""

from __future__ import annotations

import pytest

from apps.emails.models import ActionLog, Email, EmailClassification
from tests.conftest import make_classification, make_email


# ── EmailListView ──────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestEmailListView:
    URL = "/api/v1/emails/"

    def test_unauthenticated_returns_401(self, api_client):
        resp = api_client.get(self.URL)
        assert resp.status_code == 401

    def test_returns_only_requesting_users_emails(self, auth_client, user, other_user):
        make_email(user, subject="Mine")
        make_email(other_user, subject="Theirs")
        resp = auth_client.get(self.URL)
        assert resp.status_code == 200
        subjects = {e["subject"] for e in resp.data["results"]}
        assert "Mine" in subjects
        assert "Theirs" not in subjects

    def test_filter_by_priority(self, auth_client, user):
        e_crit = make_email(user, subject="Critical email")
        e_low = make_email(user, subject="Low priority email")
        make_classification(e_crit, priority="critical")
        make_classification(e_low, priority="low")
        resp = auth_client.get(self.URL, {"priority": "critical"})
        assert resp.status_code == 200
        subjects = {e["subject"] for e in resp.data["results"]}
        assert "Critical email" in subjects
        assert "Low priority email" not in subjects

    def test_filter_by_category(self, auth_client, user):
        e_billing = make_email(user, subject="Invoice")
        e_support = make_email(user, subject="Help request")
        make_classification(e_billing, category="billing")
        make_classification(e_support, category="support")
        resp = auth_client.get(self.URL, {"category": "billing"})
        assert resp.status_code == 200
        subjects = {e["subject"] for e in resp.data["results"]}
        assert "Invoice" in subjects
        assert "Help request" not in subjects

    def test_search_by_subject(self, auth_client, user):
        make_email(user, subject="Urgent billing issue")
        make_email(user, subject="Regular newsletter")
        resp = auth_client.get(self.URL, {"search": "billing"})
        assert resp.status_code == 200
        subjects = {e["subject"] for e in resp.data["results"]}
        assert "Urgent billing issue" in subjects
        assert "Regular newsletter" not in subjects

    def test_pagination_default_page_size_is_20(self, auth_client, user):
        for i in range(25):
            make_email(user, subject=f"Email {i}")
        resp = auth_client.get(self.URL)
        assert resp.status_code == 200
        assert len(resp.data["results"]) == 20
        assert resp.data["count"] == 25
        assert resp.data["next"] is not None

    def test_includes_classification_summary_in_list(self, auth_client, user):
        email = make_email(user)
        make_classification(email, summary="AI summary here")
        resp = auth_client.get(self.URL)
        assert resp.status_code == 200
        item = resp.data["results"][0]
        assert item["classification"]["summary"] == "AI summary here"

    def test_email_without_classification_has_null_classification(self, auth_client, user):
        make_email(user)
        resp = auth_client.get(self.URL)
        assert resp.status_code == 200
        assert resp.data["results"][0]["classification"] is None


# ── EmailDetailView ────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestEmailDetailView:
    def test_returns_full_detail_with_classification(self, auth_client, user):
        email = make_email(user, body_text="Full body here.")
        make_classification(email, summary="Detailed summary.")
        resp = auth_client.get(f"/api/v1/emails/{email.pk}/")
        assert resp.status_code == 200
        assert resp.data["body_text"] == "Full body here."
        assert resp.data["classification"]["summary"] == "Detailed summary."

    def test_cannot_access_other_users_email(self, auth_client, other_user):
        other_email = make_email(other_user)
        resp = auth_client.get(f"/api/v1/emails/{other_email.pk}/")
        assert resp.status_code == 404

    def test_nonexistent_email_returns_404(self, auth_client):
        resp = auth_client.get("/api/v1/emails/99999/")
        assert resp.status_code == 404


# ── EmailArchiveView ───────────────────────────────────────────────────────


@pytest.mark.django_db
class TestEmailArchiveView:
    def test_sets_is_archived_true(self, auth_client, user):
        email = make_email(user)
        resp = auth_client.post(f"/api/v1/emails/{email.pk}/archive/")
        assert resp.status_code == 200
        email.refresh_from_db()
        assert email.is_archived is True

    def test_creates_archived_action_log(self, auth_client, user):
        email = make_email(user)
        auth_client.post(f"/api/v1/emails/{email.pk}/archive/")
        assert ActionLog.objects.filter(
            email=email, action=ActionLog.ActionType.ARCHIVED
        ).exists()

    def test_cannot_archive_other_users_email(self, auth_client, other_user):
        other_email = make_email(other_user)
        resp = auth_client.post(f"/api/v1/emails/{other_email.pk}/archive/")
        assert resp.status_code == 404


# ── EmailReplyView ─────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestEmailReplyView:
    def test_creates_replied_action_log(self, auth_client, user):
        email = make_email(user)
        resp = auth_client.post(
            f"/api/v1/emails/{email.pk}/reply/",
            {"body": "Thank you for contacting us."},
            format="json",
        )
        assert resp.status_code == 200
        log = ActionLog.objects.filter(email=email, action=ActionLog.ActionType.REPLIED).first()
        assert log is not None

    def test_reply_body_stored_in_log_details(self, auth_client, user):
        email = make_email(user)
        auth_client.post(
            f"/api/v1/emails/{email.pk}/reply/",
            {"body": "We received your message."},
            format="json",
        )
        log = ActionLog.objects.get(email=email, action=ActionLog.ActionType.REPLIED)
        assert "We received your message." in log.details["body"]

    def test_cannot_reply_to_other_users_email(self, auth_client, other_user):
        other_email = make_email(other_user)
        resp = auth_client.post(
            f"/api/v1/emails/{other_email.pk}/reply/",
            {"body": "Hi"},
            format="json",
        )
        assert resp.status_code == 404


# ── EmailClassificationUpdateView ─────────────────────────────────────────


@pytest.mark.django_db
class TestEmailClassificationUpdateView:
    def test_correction_sets_user_corrected_flag(self, auth_client, user):
        email = make_email(user, status=Email.Status.CLASSIFIED)
        make_classification(email, category="support", priority="medium", sentiment="neutral")
        resp = auth_client.patch(
            f"/api/v1/emails/{email.pk}/classification/",
            {"category": "billing", "priority": "high", "sentiment": "negative"},
            format="json",
        )
        assert resp.status_code == 200
        email.classification.refresh_from_db()
        assert email.classification.user_corrected is True
        assert email.classification.category == "billing"

    def test_correction_preserves_original_values(self, auth_client, user):
        email = make_email(user, status=Email.Status.CLASSIFIED)
        make_classification(
            email,
            category="support",
            priority="medium",
            sentiment="neutral",
            original_category="",
        )
        auth_client.patch(
            f"/api/v1/emails/{email.pk}/classification/",
            {"category": "billing", "priority": "high", "sentiment": "negative"},
            format="json",
        )
        email.classification.refresh_from_db()
        assert email.classification.original_category == "support"
        assert email.classification.original_priority == "medium"

    def test_correction_without_classification_returns_404(self, auth_client, user):
        email = make_email(user)
        resp = auth_client.patch(
            f"/api/v1/emails/{email.pk}/classification/",
            {"category": "billing"},
            format="json",
        )
        assert resp.status_code == 404

    def test_creates_corrected_action_log(self, auth_client, user):
        email = make_email(user, status=Email.Status.CLASSIFIED)
        make_classification(email)
        auth_client.patch(
            f"/api/v1/emails/{email.pk}/classification/",
            {"category": "billing", "priority": "high", "sentiment": "negative"},
            format="json",
        )
        assert ActionLog.objects.filter(
            email=email, action=ActionLog.ActionType.CORRECTED
        ).exists()


# ── DashboardOverviewView ──────────────────────────────────────────────────


@pytest.mark.django_db
class TestDashboardOverviewView:
    URL = "/api/v1/dashboard/overview/"

    def test_unauthenticated_returns_401(self, api_client):
        assert api_client.get(self.URL).status_code == 401

    def test_returns_correct_total(self, auth_client, user):
        for _ in range(3):
            make_email(user)
        resp = auth_client.get(self.URL)
        assert resp.data["total"] == 3

    def test_counts_only_critical_and_high_as_urgent(self, auth_client, user):
        e1 = make_email(user)
        e2 = make_email(user)
        e3 = make_email(user)
        make_classification(e1, priority="critical")
        make_classification(e2, priority="high")
        make_classification(e3, priority="low")
        resp = auth_client.get(self.URL)
        assert resp.data["urgent"] == 2

    def test_counts_classified_by_status(self, auth_client, user):
        e1 = make_email(user, status=Email.Status.CLASSIFIED)
        e2 = make_email(user, status=Email.Status.PENDING)
        make_classification(e1)
        resp = auth_client.get(self.URL)
        assert resp.data["classified"] == 1

    def test_counts_pending_action(self, auth_client, user):
        e1 = make_email(user)
        e2 = make_email(user)
        make_classification(e1, requires_action=True)
        make_classification(e2, requires_action=False)
        resp = auth_client.get(self.URL)
        assert resp.data["pending_action"] == 1

    def test_excludes_other_users_from_counts(self, auth_client, user, other_user):
        other_email = make_email(other_user)
        make_classification(other_email, priority="critical")
        resp = auth_client.get(self.URL)
        assert resp.data["total"] == 0
        assert resp.data["urgent"] == 0


# ── DemoSeedView ───────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestDemoSeedView:
    URL = "/api/v1/demo/seed/"

    def test_returns_403_when_debug_is_false(self, auth_client, settings):
        settings.DEBUG = False
        resp = auth_client.post(self.URL)
        assert resp.status_code == 403

    def test_unauthenticated_returns_401(self, api_client, settings):
        settings.DEBUG = True
        resp = api_client.post(self.URL)
        assert resp.status_code == 401

    def test_generates_150_emails_for_authenticated_user(self, auth_client, user, settings):
        settings.DEBUG = True
        resp = auth_client.post(self.URL)
        assert resp.status_code == 200
        assert Email.objects.filter(user=user).count() == 150

    def test_generates_classifications_for_all_emails(self, auth_client, user, settings):
        settings.DEBUG = True
        auth_client.post(self.URL)
        email_count = Email.objects.filter(user=user).count()
        clf_count = EmailClassification.objects.filter(email__user=user).count()
        assert clf_count == email_count


# ── DemoResetView ──────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestDemoResetView:
    URL = "/api/v1/demo/reset/"

    def test_deletes_all_user_emails(self, auth_client, user, settings):
        settings.DEBUG = True
        for _ in range(3):
            make_email(user)
        resp = auth_client.post(self.URL)
        assert resp.status_code == 200
        assert Email.objects.filter(user=user).count() == 0

    def test_returns_403_when_not_debug(self, auth_client, settings):
        settings.DEBUG = False
        resp = auth_client.post(self.URL)
        assert resp.status_code == 403
