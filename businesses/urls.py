from django.urls import path
from .views import BusinessProfileView

urlpatterns = [
    path('profile/', BusinessProfileView.as_view(), name='business_profile'),
]
