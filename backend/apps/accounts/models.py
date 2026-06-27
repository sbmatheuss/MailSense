from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    gmail_access_token = models.TextField(blank=True)
    gmail_refresh_token = models.TextField(blank=True)
    gmail_connected_at = models.DateTimeField(null=True, blank=True)
    gmail_sync_enabled = models.BooleanField(default=False)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    timezone = models.CharField(max_length=50, default="America/Sao_Paulo")

    def __str__(self) -> str:
        return f"Profile({self.user.username})"

    @property
    def is_gmail_connected(self) -> bool:
        return bool(self.gmail_access_token and self.gmail_sync_enabled)
