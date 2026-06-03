from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from accounts.permissions import IsStudent
from .models import StudentProfile
from .serializers import StudentProfileSerializer

class StudentProfileView(generics.RetrieveUpdateAPIView):
    """
    Retrieve or Update details of the authenticated student's profile.
    Requires student role permissions.
    """
    serializer_class = StudentProfileSerializer
    permission_classes = [IsAuthenticated, IsStudent]

    def get_object(self):
        # Retrieve the StudentProfile associated with the authenticated User
        return StudentProfile.objects.get(user=self.request.user)
