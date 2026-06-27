from __future__ import annotations

from datetime import datetime

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


class GmailService:
    """Wrapper da Gmail API com retry e rate limiting."""

    SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.modify",
    ]

    def __init__(self, user_profile) -> None:
        self.credentials = self._build_credentials(user_profile)
        self.service = build("gmail", "v1", credentials=self.credentials)

    def fetch_new_messages(self, after: datetime | None = None, max_results: int = 50) -> list[dict]:
        """Busca mensagens novas desde a última sincronização."""
        raise NotImplementedError

    def get_message_detail(self, message_id: str) -> dict:
        """Retorna subject, body, headers de uma mensagem."""
        raise NotImplementedError

    def send_reply(self, thread_id: str, to: str, subject: str, body: str) -> dict:
        """Envia resposta em uma thread existente."""
        raise NotImplementedError

    def mark_as_read(self, message_id: str) -> None:
        raise NotImplementedError

    def _build_credentials(self, profile) -> Credentials:
        """Constrói credenciais OAuth2 com refresh automático."""
        raise NotImplementedError
