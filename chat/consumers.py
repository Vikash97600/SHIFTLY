import json
from django.utils import timezone
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ChatRoom, ChatParticipant, ChatMessage

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_uuid = self.scope['url_route']['kwargs']['room_uuid']
        self.room_group_name = f"chat_{self.room_uuid}"
        self.user = self.scope.get('user')

        # 1. Security Check: User is Authenticated
        if not self.user or self.user.is_anonymous:
            # Close connection with forbidden code
            await self.close(code=4003)
            return

        # 2. Security Check: User is a participant of the ChatRoom
        is_participant = await self.check_room_participant(self.room_uuid, self.user)
        if not is_participant:
            # Close connection with unauthorized code
            await self.close(code=4001)
            return

        # Add to room channel group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Leave room channel group
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except ValueError:
            return

        event_type = data.get('type')

        if event_type == 'send_message':
            message_content = data.get('message')
            message_type = data.get('message_type', 'text') # text, image, document

            if not message_content:
                return

            # Save message to DB
            msg = await self.save_message(self.room_uuid, self.user, message_type, message_content)

            # Broadcast message to room channel group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message_id': msg.id,
                    'sender_email': self.user.email,
                    'message_type': msg.message_type,
                    'message_content': msg.message_content,
                    'is_read': msg.is_read,
                    'created_at': msg.created_at.isoformat(),
                }
            )

        elif event_type == 'typing_status':
            is_typing = data.get('is_typing', False)

            # Broadcast typing status to room channel group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_typing',
                    'sender_email': self.user.email,
                    'is_typing': is_typing
                }
            )

        elif event_type == 'read_receipt':
            # Mark messages sent by counterparty in this room as read
            await self.mark_messages_read(self.room_uuid, self.user)

            # Broadcast read receipt validation
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_read_receipt',
                    'reader_email': self.user.email,
                }
            )

    # Event handlers for channel group broadcasts
    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message_id': event['message_id'],
            'sender_email': event['sender_email'],
            'message_type': event['message_type'],
            'message_content': event['message_content'],
            'is_read': event['is_read'],
            'created_at': event['created_at']
        }))

    async def chat_typing(self, event):
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'sender_email': event['sender_email'],
            'is_typing': event['is_typing']
        }))

    async def chat_read_receipt(self, event):
        await self.send(text_data=json.dumps({
            'type': 'read_receipt',
            'reader_email': event['reader_email']
        }))

    # Helper methods executing database queries asynchronously
    @database_sync_to_async
    def check_room_participant(self, room_uuid, user):
        try:
            return ChatParticipant.objects.filter(chat_room__uuid=room_uuid, user=user).exists()
        except Exception:
            return False

    @database_sync_to_async
    def save_message(self, room_uuid, user, message_type, content):
        room = ChatRoom.objects.get(uuid=room_uuid)
        return ChatMessage.objects.create(
            chat_room=room,
            sender=user,
            message_type=message_type,
            message_content=content
        )

    @database_sync_to_async
    def mark_messages_read(self, room_uuid, user):
        # Mark other participants' messages as read
        ChatMessage.objects.filter(
            chat_room__uuid=room_uuid,
            is_read=False
        ).exclude(sender=user).update(
            is_read=True,
            read_at=timezone.now()
        )
