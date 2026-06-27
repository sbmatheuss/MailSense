from rest_framework import serializers
from .models import Email, EmailClassification, ActionLog


class EmailClassificationListSerializer(serializers.ModelSerializer):
    """Lightweight classification for list view — omits heavy fields."""

    class Meta:
        model = EmailClassification
        fields = [
            "category", "priority", "sentiment",
            "confidence_score", "summary", "requires_action",
        ]


class EmailClassificationDetailSerializer(serializers.ModelSerializer):
    """Full classification for detail view."""

    class Meta:
        model = EmailClassification
        fields = [
            "category", "priority", "sentiment", "confidence_score",
            "summary", "key_topics", "suggested_reply", "urgency_reason",
            "requires_action", "user_corrected", "processed_at", "processing_time_ms",
        ]


class EmailListSerializer(serializers.ModelSerializer):
    classification = EmailClassificationListSerializer(read_only=True)

    class Meta:
        model = Email
        fields = [
            "id", "gmail_id", "from_address", "from_name", "subject",
            "received_at", "is_read", "is_archived", "has_attachments",
            "status", "classification",
        ]


class EmailDetailSerializer(serializers.ModelSerializer):
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
    class Meta:
        model = ActionLog
        fields = ["id", "action", "details", "performed_at"]
