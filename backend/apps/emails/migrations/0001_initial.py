from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Email",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("gmail_id", models.CharField(max_length=255, unique=True)),
                ("thread_id", models.CharField(max_length=255)),
                ("from_address", models.EmailField(max_length=254)),
                ("from_name", models.CharField(blank=True, max_length=255)),
                ("to_address", models.JSONField(default=list)),
                ("cc_address", models.JSONField(default=list)),
                ("subject", models.CharField(max_length=500)),
                ("body_text", models.TextField()),
                ("body_html", models.TextField(blank=True)),
                ("received_at", models.DateTimeField()),
                ("is_read", models.BooleanField(default=False)),
                ("is_archived", models.BooleanField(default=False)),
                ("snoozed_until", models.DateTimeField(blank=True, null=True)),
                ("has_attachments", models.BooleanField(default=False)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pendente"),
                            ("processing", "Processando"),
                            ("classified", "Classificado"),
                            ("failed", "Falhou"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("raw_headers", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="emails",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-received_at"],
            },
        ),
        migrations.CreateModel(
            name="EmailClassification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("support", "Suporte"),
                            ("billing", "Financeiro"),
                            ("bug", "Bug Report"),
                            ("feature", "Feature Request"),
                            ("sales", "Vendas"),
                            ("internal", "Interno"),
                            ("newsletter", "Newsletter"),
                            ("spam", "Spam"),
                            ("other", "Outro"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "priority",
                    models.CharField(
                        choices=[
                            ("critical", "Crítico"),
                            ("high", "Alto"),
                            ("medium", "Médio"),
                            ("low", "Baixo"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "sentiment",
                    models.CharField(
                        choices=[
                            ("positive", "Positivo"),
                            ("neutral", "Neutro"),
                            ("negative", "Negativo"),
                            ("urgent", "Urgente"),
                        ],
                        max_length=20,
                    ),
                ),
                ("confidence_score", models.FloatField()),
                ("summary", models.TextField()),
                ("key_topics", models.JSONField(default=list)),
                ("suggested_reply", models.TextField(blank=True)),
                ("urgency_reason", models.TextField(blank=True)),
                ("requires_action", models.BooleanField(default=False)),
                ("user_corrected", models.BooleanField(default=False)),
                ("original_category", models.CharField(blank=True, max_length=20)),
                ("original_priority", models.CharField(blank=True, max_length=20)),
                ("original_sentiment", models.CharField(blank=True, max_length=20)),
                ("processed_at", models.DateTimeField(auto_now_add=True)),
                ("processing_time_ms", models.IntegerField(default=0)),
                (
                    "email",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="classification",
                        to="emails.email",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ActionLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "action",
                    models.CharField(
                        choices=[
                            ("replied", "Respondido"),
                            ("archived", "Arquivado"),
                            ("unarchived", "Desarquivado"),
                            ("escalated", "Escalado"),
                            ("snoozed", "Adiado"),
                            ("starred", "Marcado"),
                            ("corrected", "Corrigido"),
                        ],
                        max_length=20,
                    ),
                ),
                ("details", models.JSONField(default=dict)),
                ("performed_at", models.DateTimeField(auto_now_add=True)),
                (
                    "email",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="actions",
                        to="emails.email",
                    ),
                ),
                (
                    "performed_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-performed_at"],
            },
        ),
        migrations.AddIndex(
            model_name="email",
            index=models.Index(fields=["user", "is_archived", "received_at"], name="email_inbox_idx"),
        ),
        migrations.AddIndex(
            model_name="email",
            index=models.Index(fields=["user", "status"], name="email_status_idx"),
        ),
        migrations.AddIndex(
            model_name="email",
            index=models.Index(fields=["user", "thread_id"], name="email_thread_idx"),
        ),
        migrations.AddIndex(
            model_name="actionlog",
            index=models.Index(fields=["email", "performed_at"], name="actionlog_timeline_idx"),
        ),
    ]
