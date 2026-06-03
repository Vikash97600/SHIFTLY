from django.urls import path
from .views import ChatHistoryView, ChatFileUploadView

urlpatterns = [
    path('history/<uuid:room_uuid>/', ChatHistoryView.as_view(), name='chat_history'),
    path('upload/', ChatFileUploadView.as_view(), name='chat_file_upload'),
]
