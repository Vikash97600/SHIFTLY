import json
import uuid
from django.test import TransactionTestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse
from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async
from rest_framework import status
from rest_framework.test import APITestCase

from matches.models import Match
from students.models import StudentProfile
from businesses.models import BusinessProfile
from jobs.models import JobPosting
from chat.models import ChatRoom, ChatParticipant, ChatMessage
from chat.consumers import ChatConsumer

User = get_user_model()

class ChatEngineTests(TransactionTestCase):
    def setUp(self):
        # Create users
        self.student_user = User.objects.create_user(
            email="chat_student@shiftly.com",
            password="password123",
            role="student"
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student_user,
            first_name="Bobby",
            last_name="Fisher"
        )
        
        self.business_user = User.objects.create_user(
            email="chat_employer@shiftly.com",
            password="password123",
            role="business"
        )
        self.business_profile = BusinessProfile.objects.create(
            user=self.business_user,
            company_name="Verve Coffee",
            industry="Coffee",
            business_registration_no="REG-VERVE44"
        )

        # Create JobPosting to satisfy foreign key constraints
        self.job = JobPosting.objects.create(
            business=self.business_profile,
            title="Temp Barista",
            description="Barista Shift",
            location_name="San Francisco",
            latitude=37.7749,
            longitude=-122.4194,
            base_pay=19.50,
            start_date=timezone.now().date() + timezone.timedelta(days=2),
            end_date=timezone.now().date() + timezone.timedelta(days=2),
            shift_start_time="09:00:00",
            shift_end_time="17:00:00",
            status="active"
        )

        # Create Match & ChatRoom
        self.match = Match.objects.create(
            student=self.student_profile,
            job=self.job,
            status='active'
        )
        
        # ChatRoom and ChatParticipants are created automatically by signals!
        self.room = ChatRoom.objects.get(match=self.match)
        
        # Create an unrelated user for security testing
        self.unrelated_user = User.objects.create_user(
            email="hacker@shiftly.com",
            password="password123",
            role="student"
        )

    # Helper methods running database queries asynchronously during tests
    @database_sync_to_async
    def create_message(self, room, sender, message_type, content):
        return ChatMessage.objects.create(
            chat_room=room,
            sender=sender,
            message_type=message_type,
            message_content=content
        )

    @database_sync_to_async
    def check_message_exists(self, room, sender, content):
        return ChatMessage.objects.filter(
            chat_room=room,
            sender=sender,
            message_content=content
        ).exists()

    @database_sync_to_async
    def get_message(self, room, sender):
        return ChatMessage.objects.filter(chat_room=room, sender=sender).first()

    async def test_websocket_connect_success(self):
        """
        Verify that an authenticated participant can connect to the room.
        """
        communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/{self.room.uuid}/")
        communicator.scope['user'] = self.student_user
        communicator.scope['url_route'] = {
            'kwargs': {'room_uuid': self.room.uuid}
        }
        
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        await communicator.disconnect()

    async def test_websocket_connect_with_jwt_token(self):
        """
        Verify that we can connect to the ASGI application using a JWT token in the query string.
        """
        from config.asgi import application
        from rest_framework_simplejwt.tokens import AccessToken
        token = str(AccessToken.for_user(self.student_user))

        communicator = WebsocketCommunicator(application, f"/ws/chat/{self.room.uuid}/?token={token}")
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        await communicator.disconnect()

    async def test_websocket_connect_with_session_user(self):
        """
        Verify that a user authenticated via session can connect without token.
        """
        from config.asgi import application
        communicator = WebsocketCommunicator(application, f"/ws/chat/{self.room.uuid}/")
        communicator.scope['user'] = self.student_user
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        await communicator.disconnect()

    async def test_websocket_connect_anonymous_rejected(self):
        """
        Verify that an unauthenticated user connection is rejected (4003).
        """
        from django.contrib.auth.models import AnonymousUser
        communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/{self.room.uuid}/")
        communicator.scope['user'] = AnonymousUser()
        communicator.scope['url_route'] = {
            'kwargs': {'room_uuid': self.room.uuid}
        }
        
        connected, code = await communicator.connect()
        self.assertFalse(connected)
        self.assertEqual(code, 4003)

    async def test_websocket_connect_non_participant_rejected(self):
        """
        Verify that an authenticated user who is NOT a participant is rejected (4001).
        """
        communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/{self.room.uuid}/")
        communicator.scope['user'] = self.unrelated_user
        communicator.scope['url_route'] = {
            'kwargs': {'room_uuid': self.room.uuid}
        }
        
        connected, code = await communicator.connect()
        self.assertFalse(connected)
        self.assertEqual(code, 4001)

    async def test_websocket_messaging_flow(self):
        """
        Verify message transmission, db logging, and broadcasting.
        """
        communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/{self.room.uuid}/")
        communicator.scope['user'] = self.student_user
        communicator.scope['url_route'] = {
            'kwargs': {'room_uuid': self.room.uuid}
        }
        
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Send text message
        payload = {
            'type': 'send_message',
            'message': 'Hello verve coffee!',
            'message_type': 'text'
        }
        await communicator.send_json_to(payload)

        # Receive broadcast response
        response = await communicator.receive_json_from()
        self.assertEqual(response['type'], 'message')
        self.assertEqual(response['sender_email'], self.student_user.email)
        self.assertEqual(response['message_content'], 'Hello verve coffee!')
        self.assertEqual(response['message_type'], 'text')
        self.assertFalse(response['is_read'])

        # Verify DB entry using async helper
        msg_exists = await self.check_message_exists(self.room, self.student_user, 'Hello verve coffee!')
        self.assertTrue(msg_exists)

        await communicator.disconnect()

    async def test_websocket_typing_status(self):
        """
        Verify typing indicator statuses propagate properly.
        """
        communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/{self.room.uuid}/")
        communicator.scope['user'] = self.student_user
        communicator.scope['url_route'] = {
            'kwargs': {'room_uuid': self.room.uuid}
        }
        
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Send typing is True
        await communicator.send_json_to({
            'type': 'typing_status',
            'is_typing': True
        })

        response = await communicator.receive_json_from()
        self.assertEqual(response['type'], 'typing')
        self.assertEqual(response['sender_email'], self.student_user.email)
        self.assertTrue(response['is_typing'])

        await communicator.disconnect()

    async def test_websocket_read_receipts(self):
        """
        Verify read receipt triggers mark DB messages as read.
        """
        # Save a message from the business user (so the student can mark it read) using async helper
        await self.create_message(self.room, self.business_user, 'text', 'See you tomorrow')

        communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/{self.room.uuid}/")
        communicator.scope['user'] = self.student_user
        communicator.scope['url_route'] = {
            'kwargs': {'room_uuid': self.room.uuid}
        }
        
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Send read receipt signal
        await communicator.send_json_to({
            'type': 'read_receipt'
        })

        response = await communicator.receive_json_from()
        self.assertEqual(response['type'], 'read_receipt')
        self.assertEqual(response['reader_email'], self.student_user.email)

        # Verify DB state of business message using async helper
        msg = await self.get_message(self.room, self.business_user)
        self.assertTrue(msg.is_read)

        await communicator.disconnect()


class ChatRESTAPITests(APITestCase):
    def setUp(self):
        self.student_user = User.objects.create_user(
            email="api_student@shiftly.com",
            password="password123",
            role="student"
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student_user,
            first_name="Bobby",
            last_name="Fisher"
        )
        
        self.business_user = User.objects.create_user(
            email="api_employer@shiftly.com",
            password="password123",
            role="business"
        )
        self.business_profile = BusinessProfile.objects.create(
            user=self.business_user,
            company_name="Verve Coffee",
            industry="Coffee",
            business_registration_no="REG-VERVE44"
        )

        # Create JobPosting
        self.job = JobPosting.objects.create(
            business=self.business_profile,
            title="Acme Shift",
            description="Barista Shift",
            location_name="San Francisco",
            latitude=37.7749,
            longitude=-122.4194,
            base_pay=18.00,
            start_date=timezone.now().date() + timezone.timedelta(days=2),
            end_date=timezone.now().date() + timezone.timedelta(days=2),
            shift_start_time="08:00:00",
            shift_end_time="16:00:00",
            status="active"
        )

        self.match = Match.objects.create(
            student=self.student_profile,
            job=self.job,
            status='active'
        )
        self.room = ChatRoom.objects.get(match=self.match)

        # Unrelated user
        self.unrelated_user = User.objects.create_user(
            email="hacker_api@shiftly.com",
            password="password123",
            role="student"
        )

    def get_jwt_token(self, email, password):
        login_url = reverse('login')
        response = self.client.post(login_url, {"email": email, "password": password}, format='json')
        return response.data['access']

    def test_history_endpoint_access_control(self):
        """
        Verify security bounds on ChatHistoryView REST API.
        """
        history_url = reverse('chat_history', args=[self.room.uuid])
        
        # 1. Anonymous access is unauthorized (401)
        response = self.client.get(history_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # 2. Authenticating as unrelated user yields Forbidden (403)
        hacker_token = self.get_jwt_token("hacker_api@shiftly.com", "password123")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {hacker_token}')
        response = self.client.get(history_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 3. Authenticating as participant yields Success (200 OK)
        student_token = self.get_jwt_token("api_student@shiftly.com", "password123")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {student_token}')
        response = self.client.get(history_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
