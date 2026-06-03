from rest_framework import serializers
from .models import ChatMessage

class ChatMessageSerializer(serializers.ModelSerializer):
    sender_email = serializers.EmailField(source='sender.email', read_only=True)

    class Meta:
        model = ChatMessage
        fields = (
            'id', 'sender_email', 'message_type', 'message_content',
            'is_read', 'read_at', 'created_at'
        )
        read_only_fields = ('id', 'sender_email', 'is_read', 'read_at', 'created_at')
