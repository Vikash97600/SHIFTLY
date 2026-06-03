from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView
from django.db.models import Q
from rest_framework import viewsets, permissions
from rest_framework.permissions import IsAuthenticated

from .models import Match
from .serializers import MatchSerializer
from students.views import StudentRequiredMixin
from students.models import StudentProfile
from businesses.views import BusinessRequiredMixin
from businesses.models import BusinessProfile

class MatchViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows matches to be viewed.
    Automatically filters matches based on the authenticated user's role.
    """
    serializer_class = MatchSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'student':
            profile = get_object_or_404(StudentProfile, user=user)
            return Match.objects.filter(student=profile, status='active').select_related('student', 'job__business')
        elif user.role == 'business':
            profile = get_object_or_404(BusinessProfile, user=user)
            return Match.objects.filter(job__business=profile, status='active').select_related('student', 'job__business')
        return Match.objects.none()


class StudentMatchesView(StudentRequiredMixin, TemplateView):
    """
    Web page dashboard rendering active matches for the authenticated student.
    """
    template_name = 'students/matches.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = get_object_or_404(StudentProfile, user=self.request.user)
        matches = Match.objects.filter(student=profile, status='active').select_related('job__business')
        context.update({
            'profile': profile,
            'matches': matches,
        })
        return context


class BusinessMatchesView(BusinessRequiredMixin, TemplateView):
    """
    Web page dashboard rendering active matches for the authenticated business owner.
    """
    template_name = 'businesses/matches.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = get_object_or_404(BusinessProfile, user=self.request.user)
        matches = Match.objects.filter(job__business=profile, status='active').select_related('student', 'job')
        context.update({
            'profile': profile,
            'matches': matches,
        })
        return context
