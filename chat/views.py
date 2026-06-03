import os
import uuid
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.core.exceptions import PermissionDenied

from .models import ChatRoom, ChatParticipant, ChatMessage
from .serializers import ChatMessageSerializer

class ChatHistoryView(generics.ListAPIView):
    """
    API endpoint that returns historical messages for a specific ChatRoom.
    Validates that the authenticated user is a participant of the room.
    """
    serializer_class = ChatMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        room_uuid = self.kwargs['room_uuid']
        room = get_object_or_404(ChatRoom, uuid=room_uuid)

        # Security check: User must be a participant in the room
        is_participant = ChatParticipant.objects.filter(chat_room=room, user=self.request.user).exists()
        if not is_participant:
            raise PermissionDenied("You are not a participant in this chat room.")

        # Automatically mark all messages from other users as read
        ChatMessage.objects.filter(
            chat_room=room,
            is_read=False
        ).exclude(sender=self.request.user).update(is_read=True)

        return ChatMessage.objects.filter(chat_room=room).order_by('created_at')


class ChatFileUploadView(APIView):
    """
    API endpoint that handles secure file uploads for messaging.
    Validates extension formats and restricts file size under 5MB.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response({'error': 'No file uploaded'}, status=status.HTTP_400_BAD_REQUEST)

        # Validate file size (under 5MB)
        if uploaded_file.size > 5 * 1024 * 1024:
            return Response({'error': 'File size exceeds 5MB limit.'}, status=status.HTTP_400_BAD_REQUEST)

        ext = os.path.splitext(uploaded_file.name)[1].lower()
        image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.webp']
        doc_extensions = ['.pdf', '.doc', '.docx', '.txt', '.csv', '.xlsx']

        if ext in image_extensions:
            message_type = 'image'
        elif ext in doc_extensions:
            message_type = 'document'
        else:
            return Response({'error': 'Unsupported file format.'}, status=status.HTTP_400_BAD_REQUEST)

        # Save file with unique filename to prevent namespace overrides
        unique_filename = f"{uuid.uuid4().hex}{ext}"
        save_path = f"chat_uploads/{unique_filename}"
        
        saved_name = default_storage.save(save_path, ContentFile(uploaded_file.read()))
        file_url = default_storage.url(saved_name)

        return Response({
            'file_url': file_url,
            'file_name': uploaded_file.name,
            'message_type': message_type
        }, status=status.HTTP_201_CREATED)
