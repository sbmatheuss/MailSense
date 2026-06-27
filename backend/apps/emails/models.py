from django.db import models
from django.contrib.auth.models import User


class Email(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        PROCESSING = "processing", "Processando"
        CLASSIFIED = "classified", "Classificado"
        FAILED = "failed", "Falhou"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="emails")
    # unique=True already creates a btree index — db_index=True would be a duplicate
    gmail_id = models.CharField(max_length=255, unique=True)
    thread_id = models.CharField(max_length=255)
    from_address = models.EmailField()
    from_name = models.CharField(max_length=255, blank=True)
    to_address = models.JSONField(default=list)
    cc_address = models.JSONField(default=list)
    subject = models.CharField(max_length=500)
    body_text = models.TextField()
    body_html = models.TextField(blank=True)
    received_at = models.DateTimeField()
    is_read = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    snoozed_until = models.DateTimeField(null=True, blank=True)
    has_attachments = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    raw_headers = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-received_at"]
        indexes = [
            # Most common query: inbox for a user, excluding archived
            models.Index(fields=["user", "is_archived", "received_at"], name="email_inbox_idx"),
            # Classification pipeline: find pending emails to classify
            models.Index(fields=["user", "status"], name="email_status_idx"),
            # Thread view: all emails in a thread for a user
            models.Index(fields=["user", "thread_id"], name="email_thread_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.subject} ({self.from_address})"


class EmailClassification(models.Model):
    class Category(models.TextChoices):
        SUPPORT = "support", "Suporte"
        BILLING = "billing", "Financeiro"
        BUG = "bug", "Bug Report"
        FEATURE = "feature", "Feature Request"
        SALES = "sales", "Vendas"
        INTERNAL = "internal", "Interno"
        NEWSLETTER = "newsletter", "Newsletter"
        SPAM = "spam", "Spam"
        OTHER = "other", "Outro"

    class Priority(models.TextChoices):
        CRITICAL = "critical", "Crítico"
        HIGH = "high", "Alto"
        MEDIUM = "medium", "Médio"
        LOW = "low", "Baixo"

    class Sentiment(models.TextChoices):
        POSITIVE = "positive", "Positivo"
        NEUTRAL = "neutral", "Neutro"
        NEGATIVE = "negative", "Negativo"
        URGENT = "urgent", "Urgente"

    email = models.OneToOneField(Email, on_delete=models.CASCADE, related_name="classification")
    category = models.CharField(max_length=20, choices=Category.choices)
    priority = models.CharField(max_length=20, choices=Priority.choices)
    sentiment = models.CharField(max_length=20, choices=Sentiment.choices)
    # Stored as float (0.0–1.0); precision sufficient for display/sorting purposes
    confidence_score = models.FloatField()
    summary = models.TextField()
    key_topics = models.JSONField(default=list)
    suggested_reply = models.TextField(blank=True)
    urgency_reason = models.TextField(blank=True)
    requires_action = models.BooleanField(default=False)
    # Feedback loop: track whether user overrode the AI classification
    user_corrected = models.BooleanField(default=False)
    original_category = models.CharField(max_length=20, blank=True)
    original_priority = models.CharField(max_length=20, blank=True)
    original_sentiment = models.CharField(max_length=20, blank=True)
    processed_at = models.DateTimeField(auto_now_add=True)
    processing_time_ms = models.IntegerField(default=0)

    def __str__(self) -> str:
        return f"{self.category}/{self.priority} — {self.email.subject}"


class ActionLog(models.Model):
    class ActionType(models.TextChoices):
        REPLIED = "replied", "Respondido"
        ARCHIVED = "archived", "Arquivado"
        UNARCHIVED = "unarchived", "Desarquivado"
        ESCALATED = "escalated", "Escalado"
        SNOOZED = "snoozed", "Adiado"
        STARRED = "starred", "Marcado"
        CORRECTED = "corrected", "Corrigido"

    email = models.ForeignKey(Email, on_delete=models.CASCADE, related_name="actions")
    action = models.CharField(max_length=20, choices=ActionType.choices)
    details = models.JSONField(default=dict)
    performed_by = models.ForeignKey(User, on_delete=models.CASCADE)
    performed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-performed_at"]
        indexes = [
            models.Index(fields=["email", "performed_at"], name="actionlog_timeline_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.action} — {self.email.subject}"
