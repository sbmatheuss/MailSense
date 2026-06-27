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
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        UserProfile.objects.create(user=user)
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "user_id": user.pk}, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        user = authenticate(username=request.data.get("username"), password=request.data.get("password"))
        if not user:
            return Response({"detail": "Credenciais inválidas."}, status=status.HTTP_401_UNAUTHORIZED)
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "user_id": user.pk})


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        return Response(UserProfileSerializer(profile).data)


class GmailConnectView(APIView):
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
    permission_classes = [IsAuthenticated]

    def post(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        profile.gmail_access_token = ""
        profile.gmail_refresh_token = ""
        profile.gmail_sync_enabled = False
        profile.gmail_connected_at = None
        profile.save()
        return Response({"detail": "Gmail desconectado."})
