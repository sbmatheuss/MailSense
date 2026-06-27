from rest_framework import serializers
from .models import Email, EmailClassification, ActionLog


class EmailClassificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailClassification
        fields = [
            "category", "priority", "sentiment", "confidence_score",
            "summary", "key_topics", "suggested_reply", "urgency_reason",
            "requires_action", "user_corrected", "processed_at", "processing_time_ms",
        ]


class EmailListSerializer(serializers.ModelSerializer):
    classification = EmailClassificationSerializer(read_only=True)

    class Meta:
        model = Email
        fields = [
            "id", "gmail_id", "from_address", "from_name", "subject",
            "received_at", "is_read", "has_attachments", "status", "classification",
        ]


class EmailDetailSerializer(serializers.ModelSerializer):
    classification = EmailClassificationSerializer(read_only=True)

    class Meta:
        model = Email
        fields = [
            "id", "gmail_id", "thread_id", "from_address", "from_name",
            "to_address", "cc_address", "subject", "body_text", "body_html",
            "received_at", "is_read", "has_attachments", "status",
            "raw_headers", "created_at", "classification",
        ]


class EmailClassificationUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailClassification
        fields = ["category", "priority", "sentiment"]

    def update(self, instance, validated_data):
        if not instance.user_corrected:
            instance.original_category = instance.category
        instance.user_corrected = True
        return super().update(instance, validated_data)


class ActionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActionLog
        fields = ["id", "action", "details", "performed_at"]
