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
            name="UserProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("gmail_access_token", models.TextField(blank=True)),
                ("gmail_refresh_token", models.TextField(blank=True)),
                ("gmail_connected_at", models.DateTimeField(blank=True, null=True)),
                ("gmail_sync_enabled", models.BooleanField(default=False)),
                ("last_sync_at", models.DateTimeField(blank=True, null=True)),
                ("timezone", models.CharField(default="America/Sao_Paulo", max_length=50)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profile",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
