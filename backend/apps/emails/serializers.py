from rest_framework import serializers
from .models import Email, EmailClassification, ActionLog


class EmailClassificationListSerializer(serializers.ModelSerializer):
    """Classificação resumida para listagem — omite campos pesados (key_topics, suggested_reply).

    Mantém apenas os campos necessários para renderizar badges e indicadores
    na lista de e-mails. Reduz o payload por item em ~50% vs. o serializer completo.
    """

    class Meta:
        model = EmailClassification
        fields = [
            "category", "priority", "sentiment",
            "confidence_score", "summary", "requires_action",
        ]


class EmailClassificationDetailSerializer(serializers.ModelSerializer):
    """Classificação completa para visualização de detalhe.

    Inclui todos os campos gerados pela IA, metadados de processamento e
    estado do feedback loop (user_corrected, original_*).
    """

    class Meta:
        model = EmailClassification
        fields = [
            "category", "priority", "sentiment", "confidence_score",
            "summary", "key_topics", "suggested_reply", "urgency_reason",
            "requires_action", "user_corrected", "processed_at", "processing_time_ms",
        ]


class EmailListSerializer(serializers.ModelSerializer):
    """Serializer de listagem — retorna apenas campos necessários para a inbox list view.

    O campo `classification` usa o serializer resumido (6 campos) para manter
    o payload pequeno. Para detalhes completos usar `EmailDetailSerializer`.
    """

    classification = EmailClassificationListSerializer(read_only=True)

    class Meta:
        model = Email
        fields = [
            "id", "gmail_id", "from_address", "from_name", "subject",
            "received_at", "is_read", "is_archived", "has_attachments",
            "status", "classification",
        ]


class EmailDetailSerializer(serializers.ModelSerializer):
    """Serializer de detalhe — retorna todos os campos incluindo body e histórico de ações.

    `actions` retorna os últimos 10 ActionLogs via `get_actions`. Limitado a 10
    para evitar payloads excessivos em threads muito longas.
    """

    classification = EmailClassificationDetailSerializer(read_only=True)
    actions = serializers.SerializerMethodField()

    class Meta:
        model = Email
        fields = [
            "id", "gmail_id", "thread_id", "from_address", "from_name",
            "to_address", "cc_address", "subject", "body_text", "body_html",
            "received_at", "is_read", "is_archived", "snoozed_until",
            "has_attachments", "status", "created_at", "classification", "actions",
        ]

    def get_actions(self, obj) -> list:
        return ActionLogSerializer(obj.actions.all()[:10], many=True).data


class EmailClassificationUpdateSerializer(serializers.ModelSerializer):
    """Serializer para PATCH de classificação pelo usuário (feedback loop).

    Na primeira correção, preserva os valores originais em `original_*` e seta
    `user_corrected=True`. Correções subsequentes apenas atualizam os valores,
    pois o snapshot original já está preservado da primeira vez.
    """

    class Meta:
        model = EmailClassification
        fields = ["category", "priority", "sentiment"]

    def update(self, instance, validated_data):
        if not instance.user_corrected:
            instance.original_category = instance.category
            instance.original_priority = instance.priority
            instance.original_sentiment = instance.sentiment
        instance.user_corrected = True
        return super().update(instance, validated_data)


class ActionLogSerializer(serializers.ModelSerializer):
    """Serializer somente-leitura para o histórico de ações de um e-mail."""

    class Meta:
        model = ActionLog
        fields = ["id", "action", "details", "performed_at"]
