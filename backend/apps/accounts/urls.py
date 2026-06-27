from django.urls import path
from . import views

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="auth-register"),
    path("login/", views.LoginView.as_view(), name="auth-login"),
    path("profile/", views.ProfileView.as_view(), name="auth-profile"),
    path("gmail/connect/", views.GmailConnectView.as_view(), name="gmail-connect"),
    path("gmail/callback/", views.GmailCallbackView.as_view(), name="gmail-callback"),
    path("gmail/disconnect/", views.GmailDisconnectView.as_view(), name="gmail-disconnect"),
]
