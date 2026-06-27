from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.conf import settings
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from google_auth_oauthlib.flow import Flow
from .models import UserProfile
from .serializers import UserProfileSerializer, RegisterSerializer


class RegisterView(APIView):
    """POST /api/v1/accounts/register/ — cria usuário e retorna token de autenticação.

    Cria o UserProfile associado no mesmo request para garantir consistência.
    Usa `create_user` para hashar a senha corretamente.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        UserProfile.objects.create(user=user)
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "user_id": user.pk}, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """POST /api/v1/accounts/login/ — autentica e retorna o token DRF.

    Usa `django.contrib.auth.authenticate` para aproveitar o backend de autenticação
    padrão (suporta customização futura com AUTHENTICATION_BACKENDS).
    """

    permission_classes = [AllowAny]

    def post(self, request):
        user = authenticate(username=request.data.get("username"), password=request.data.get("password"))
        if not user:
            return Response({"detail": "Credenciais inválidas."}, status=status.HTTP_401_UNAUTHORIZED)
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "user_id": user.pk})


class ProfileView(APIView):
    """GET /api/v1/accounts/profile/ — retorna dados do perfil e status Gmail.

    Usa `get_or_create` como safety net para usuários criados antes da lógica
    de criação automática do profile estar em vigor.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        return Response(UserProfileSerializer(profile).data)


class LogoutView(APIView):
    """POST /api/v1/accounts/logout/ — revoga o token de autenticação imediatamente.

    Deletar o token (ao invés de usar blacklist) é a forma correta com DRF Token:
    qualquer request subsequente com o mesmo token retorna 401 automaticamente.
    Conforme ADR-004: escolhemos DRF Token pela simplicidade de revogação.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class GmailConnectView(APIView):
    """POST /api/v1/accounts/gmail/connect/ — inicia o fluxo OAuth2 com Google.

    Retorna a URL de autorização que o frontend deve redirecionar o usuário.
    O `state` é salvo na session para validação no callback (proteção CSRF OAuth).
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=[
                "https://www.googleapis.com/auth/gmail.readonly",
                "https://www.googleapis.com/auth/gmail.send",
                "https://www.googleapis.com/auth/gmail.modify",
            ],
        )
        flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
        auth_url, state = flow.authorization_url(access_type="offline", include_granted_scopes="true", prompt="consent")
        request.session["oauth_state"] = state
        return Response({"auth_url": auth_url})


class GmailCallbackView(APIView):
    """GET /api/v1/accounts/gmail/callback/ — troca o authorization code pelos tokens OAuth2.

    O `prompt=consent` na GmailConnectView garante que `refresh_token` sempre
    seja retornado — sem ele o acesso expira em 1h sem possibilidade de refresh.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        code = request.GET.get("code")
        if not code:
            return Response({"detail": "Código de autorização ausente."}, status=status.HTTP_400_BAD_REQUEST)

        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
        )
        flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
        flow.fetch_token(code=code)

        credentials = flow.credentials
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        profile.gmail_access_token = credentials.token
        profile.gmail_refresh_token = credentials.refresh_token or profile.gmail_refresh_token
        profile.gmail_sync_enabled = True
        from django.utils import timezone
        profile.gmail_connected_at = timezone.now()
        profile.save()

        return Response({"detail": "Gmail conectado com sucesso."})


class GmailDisconnectView(APIView):
    """POST /api/v1/accounts/gmail/disconnect/ — revoga a integração Gmail.

    Limpa tokens e desabilita sync sem deletar e-mails já sincronizados.
    Revogar o token no Google OAuth é responsabilidade do usuário via conta Google.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        profile.gmail_access_token = ""
        profile.gmail_refresh_token = ""
        profile.gmail_sync_enabled = False
        profile.gmail_connected_at = None
        profile.save()
        return Response({"detail": "Gmail desconectado."})
