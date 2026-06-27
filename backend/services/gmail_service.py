from __future__ import annotations

import base64
import email as email_lib
import logging
from datetime import datetime, timezone

from django.conf import settings
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]


class GmailAuthError(Exception):
    """Raised when OAuth2 credentials are missing or cannot be refreshed."""


class GmailService:
    """Wrapper da Gmail API com retry, rate limiting e refresh automático de tokens.

    Usage::

        service = GmailService(user_profile)
        messages = service.fetch_new_messages(after=last_sync_at)
    """

    def __init__(self, user_profile) -> None:
        self.profile = user_profile
        self.credentials = self._build_credentials(user_profile)
        self.service = build("gmail", "v1", credentials=self.credentials, cache_discovery=False)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch_new_messages(self, after: datetime | None = None, max_results: int = 50) -> list[dict]:
        """Busca mensagens novas desde *after* (ou todas se None).

        Returns a list of parsed message dicts ready to be saved as Email objects.
        Fetches full message details in individual calls — batching is handled
        at the Celery task level to stay within Gmail API rate limits.
        """
        query = self._build_query(after)
        try:
            response = (
                self.service.users()
                .messages()
                .list(userId="me", q=query, maxResults=max_results)
                .execute()
            )
        except HttpError as exc:
            logger.error("Gmail list error for user %s: %s", self.profile.user_id, exc)
            raise

        message_stubs = response.get("messages", [])
        if not message_stubs:
            return []

        messages = []
        for stub in message_stubs:
            try:
                detail = self.get_message_detail(stub["id"])
                messages.append(detail)
            except HttpError as exc:
                logger.warning("Could not fetch message %s: %s", stub["id"], exc)
                continue

        return messages

    def get_message_detail(self, message_id: str) -> dict:
        """Retorna subject, body_text, body_html e headers de uma mensagem.

        Returns a dict matching the Email model's field names for direct use
        in Email.objects.create(**detail).
        """
        raw = (
            self.service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )
        return self._parse_message(raw)

    def send_reply(self, thread_id: str, to: str, subject: str, body: str) -> dict:
        """Envia resposta em uma thread existente.

        Returns the sent message resource from the Gmail API.
        """
        message = self._build_mime_message(to=to, subject=f"Re: {subject}", body=body, thread_id=thread_id)
        try:
            result = (
                self.service.users()
                .messages()
                .send(userId="me", body={"raw": message, "threadId": thread_id})
                .execute()
            )
            return result
        except HttpError as exc:
            logger.error("Gmail send error for thread %s: %s", thread_id, exc)
            raise

    def mark_as_read(self, message_id: str) -> None:
        """Remove o label UNREAD da mensagem."""
        try:
            self.service.users().messages().modify(
                userId="me",
                id=message_id,
                body={"removeLabelIds": ["UNREAD"]},
            ).execute()
        except HttpError as exc:
            logger.warning("Could not mark message %s as read: %s", message_id, exc)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_credentials(self, profile) -> Credentials:
        """Constrói credenciais OAuth2 com refresh automático.

        Persists refreshed tokens back to UserProfile to avoid re-auth loops.
        Raises GmailAuthError if tokens are missing or refresh fails.
        """
        if not profile.gmail_access_token or not profile.gmail_refresh_token:
            raise GmailAuthError(f"User {profile.user_id} has no Gmail tokens stored.")

        credentials = Credentials(
            token=profile.gmail_access_token,
            refresh_token=profile.gmail_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            scopes=SCOPES,
        )

        if credentials.expired and credentials.refresh_token:
            try:
                credentials.refresh(Request())
                # Persist the new access token so next call doesn't need to refresh again
                profile.gmail_access_token = credentials.token
                profile.save(update_fields=["gmail_access_token"])
            except Exception as exc:
                raise GmailAuthError(f"Token refresh failed for user {profile.user_id}: {exc}") from exc

        return credentials

    def _build_query(self, after: datetime | None) -> str:
        """Builds a Gmail search query string."""
        parts = ["in:inbox"]
        if after:
            # Gmail uses Unix timestamp in the `after:` filter
            ts = int(after.timestamp())
            parts.append(f"after:{ts}")
        return " ".join(parts)

    def _parse_message(self, raw: dict) -> dict:
        """Converte a resposta bruta da Gmail API para um dict compatível com o model Email."""
        headers = {h["name"].lower(): h["value"] for h in raw.get("payload", {}).get("headers", [])}

        subject = headers.get("subject", "(sem assunto)")
        from_raw = headers.get("from", "")
        from_name, from_address = self._parse_email_address(from_raw)
        to_raw = headers.get("to", "")
        cc_raw = headers.get("cc", "")

        date_str = headers.get("date", "")
        received_at = self._parse_date(date_str)

        body_text, body_html = self._extract_body(raw.get("payload", {}))

        return {
            "gmail_id": raw["id"],
            "thread_id": raw.get("threadId", ""),
            "from_address": from_address,
            "from_name": from_name,
            "to_address": [a.strip() for a in to_raw.split(",") if a.strip()],
            "cc_address": [a.strip() for a in cc_raw.split(",") if a.strip()],
            "subject": subject[:500],
            "body_text": body_text,
            "body_html": body_html,
            "received_at": received_at,
            "has_attachments": self._has_attachments(raw.get("payload", {})),
            "raw_headers": {h["name"]: h["value"] for h in raw.get("payload", {}).get("headers", [])},
        }

    def _parse_email_address(self, raw: str) -> tuple[str, str]:
        """Splits 'Name <email@domain>' into (name, email)."""
        parsed = email_lib.utils.parseaddr(raw)
        name, address = parsed
        return name or "", address or raw

    def _parse_date(self, date_str: str) -> datetime:
        """Parses RFC 2822 date from Gmail headers into a timezone-aware datetime."""
        try:
            parsed = email_lib.utils.parsedate_to_datetime(date_str)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except Exception:
            return datetime.now(tz=timezone.utc)

    def _extract_body(self, payload: dict) -> tuple[str, str]:
        """Extracts plain text and HTML body from a Gmail message payload."""
        body_text = ""
        body_html = ""

        mime_type = payload.get("mimeType", "")
        parts = payload.get("parts", [])

        if mime_type == "text/plain":
            body_text = self._decode_body(payload.get("body", {}).get("data", ""))
        elif mime_type == "text/html":
            body_html = self._decode_body(payload.get("body", {}).get("data", ""))
        elif parts:
            for part in parts:
                part_mime = part.get("mimeType", "")
                if part_mime == "text/plain" and not body_text:
                    body_text = self._decode_body(part.get("body", {}).get("data", ""))
                elif part_mime == "text/html" and not body_html:
                    body_html = self._decode_body(part.get("body", {}).get("data", ""))
                elif part_mime.startswith("multipart/"):
                    sub_text, sub_html = self._extract_body(part)
                    body_text = body_text or sub_text
                    body_html = body_html or sub_html

        return body_text, body_html

    def _decode_body(self, data: str) -> str:
        """Decodes base64url-encoded Gmail body data."""
        if not data:
            return ""
        try:
            return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
        except Exception:
            return ""

    def _has_attachments(self, payload: dict) -> bool:
        """Returns True if any part of the message is an attachment."""
        for part in payload.get("parts", []):
            if part.get("filename"):
                return True
            if self._has_attachments(part):
                return True
        return False

    def _build_mime_message(self, to: str, subject: str, body: str, thread_id: str) -> str:
        """Builds a base64url-encoded MIME message for the Gmail send API."""
        from email.mime.text import MIMEText
        msg = MIMEText(body, "plain", "utf-8")
        msg["To"] = to
        msg["Subject"] = subject
        return base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
