from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from accounts.permissions import IsBusiness
from .models import BusinessProfile
from .serializers import BusinessProfileSerializer

class BusinessProfileView(generics.RetrieveUpdateAPIView):
    """
    Retrieve or Update details of the authenticated business owner's profile.
    Requires business owner role permissions.
    """
    serializer_class = BusinessProfileSerializer
    permission_classes = [IsAuthenticated, IsBusiness]

    def get_object(self):
        # Retrieve the BusinessProfile associated with the authenticated User
        return BusinessProfile.objects.get(user=self.request.user)
