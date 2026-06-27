import os
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.contrib.auth.models import AnonymousUser
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

django_asgi_app = get_asgi_application()

from apps.emails.routing import websocket_urlpatterns  # noqa: E402


@database_sync_to_async
def _user_from_token(key: str):
    from rest_framework.authtoken.models import Token
    try:
        return Token.objects.select_related("user").get(key=key).user
    except Token.DoesNotExist:
        return AnonymousUser()


class TokenAuthMiddleware:
    """Resolves DRF token passed as ?token=<key> query param for WebSocket auth."""

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        params = parse_qs(scope.get("query_string", b"").decode())
        key = (params.get("token") or [None])[0]
        if key:
            scope["user"] = await _user_from_token(key)
        elif "user" not in scope:
            scope["user"] = AnonymousUser()
        return await self.inner(scope, receive, send)


application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            TokenAuthMiddleware(URLRouter(websocket_urlpatterns))
        ),
    }
)
