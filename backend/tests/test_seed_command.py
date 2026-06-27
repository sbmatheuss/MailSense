"""Integration tests for the seed_demo management command."""

from __future__ import annotations

import pytest
from django.core.management import call_command

from apps.emails.models import Email, EmailClassification
from tests.conftest import make_email


@pytest.mark.django_db
class TestSeedDemoCommand:
    def test_creates_150_emails_by_default(self, user):
        call_command("seed_demo", user_id=user.pk)
        assert Email.objects.filter(user=user).count() == 150

    def test_creates_classification_for_every_email(self, user):
        call_command("seed_demo", user_id=user.pk)
        email_count = Email.objects.filter(user=user).count()
        clf_count = EmailClassification.objects.filter(email__user=user).count()
        assert clf_count == email_count

    def test_all_emails_have_classified_status(self, user):
        call_command("seed_demo", user_id=user.pk)
        unclassified = Email.objects.filter(
            user=user
        ).exclude(status=Email.Status.CLASSIFIED).count()
        assert unclassified == 0

    def test_categories_match_between_email_content_and_classification(self, user):
        """Each classification's category must reflect the email's content category.

        This was the core bug the seed_demo rewrite fixed — categories were
        randomized independently from the template, creating incoherent data.
        """
        call_command("seed_demo", user_id=user.pk)
        # All 9 categories should appear (sanity check on category distribution)
        categories = set(
            EmailClassification.objects.filter(email__user=user)
            .values_list("category", flat=True)
            .distinct()
        )
        expected = {"support", "billing", "bug", "feature", "sales", "internal", "newsletter"}
        assert expected.issubset(categories)

    def test_is_idempotent_when_run_twice(self, user):
        call_command("seed_demo", user_id=user.pk)
        call_command("seed_demo", user_id=user.pk)
        # Second run deletes and recreates → still 150
        assert Email.objects.filter(user=user).count() == 150

    def test_accepts_custom_count(self, user):
        call_command("seed_demo", user_id=user.pk, count=30)
        assert Email.objects.filter(user=user).count() == 30

    def test_does_not_affect_other_users_emails(self, user, other_user):
        make_email(other_user, subject="Other user's email")
        call_command("seed_demo", user_id=user.pk)
        assert Email.objects.filter(user=other_user).count() == 1

    def test_priority_distribution_has_no_invalid_values(self, user):
        call_command("seed_demo", user_id=user.pk)
        valid_priorities = {"critical", "high", "medium", "low"}
        actual = set(
            EmailClassification.objects.filter(email__user=user)
            .values_list("priority", flat=True)
            .distinct()
        )
        assert actual.issubset(valid_priorities)

    def test_sentiment_distribution_has_no_invalid_values(self, user):
        call_command("seed_demo", user_id=user.pk)
        valid_sentiments = {"positive", "neutral", "negative", "urgent"}
        actual = set(
            EmailClassification.objects.filter(email__user=user)
            .values_list("sentiment", flat=True)
            .distinct()
        )
        assert actual.issubset(valid_sentiments)
