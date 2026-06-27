from django.contrib.auth.models import User
from rest_framework import serializers
from .models import UserProfile


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer de registro — valida e cria User com senha hasheada.

    `password` é write_only para nunca ser retornado em nenhuma resposta.
    min_length=8 aplicado no nível do serializer para feedback imediato ao cliente.
    """

    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["username", "email", "password"]

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer de leitura do perfil — expõe dados do User e status de integração Gmail.

    `is_gmail_connected` é uma property do model que combina access_token e
    gmail_sync_enabled — nunca expõe os tokens diretamente.
    """

    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    is_gmail_connected = serializers.BooleanField(read_only=True)

    class Meta:
        model = UserProfile
        fields = ["username", "email", "is_gmail_connected", "gmail_connected_at", "last_sync_at", "timezone"]
