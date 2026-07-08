from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import TemplateView, UpdateView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.db import transaction
from django.utils import timezone
from django.contrib import messages
from django.urls import reverse_lazy

from rest_framework import generics as drf_generics
from rest_framework.permissions import IsAuthenticated
from accounts.permissions import IsStudent
from django.contrib.auth import get_user_model
from .serializers import StudentProfileSerializer

from .models import StudentProfile, StudentSkill, Skill
from .forms import StudentProfileForm
from jobs.models import JobPosting
from swipes.models import Swipe
from matches.models import Match, JobApplication
from businesses.models import Earning
from notifications.models import Notification

User = get_user_model()

class StudentRequiredMixin(LoginRequiredMixin):
    """
    Mixin that ensures the user is logged in and possesses the 'student' role.
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.role != 'student' or not request.user.is_active or request.user.status != User.AccountStatus.APPROVED:
            raise PermissionDenied("Only approved students can access this area.")
        return super().dispatch(request, *args, **kwargs)


class StudentDashboardView(StudentRequiredMixin, TemplateView):
    template_name = 'students/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = get_object_or_404(StudentProfile, user=self.request.user)
        
        # Calculate stats
        completed_shifts = Earning.objects.filter(student=profile, payment_status='released').count()
        total_earnings = sum(e.net_amount for e in Earning.objects.filter(student=profile, payment_status='released'))
        active_apps = JobApplication.objects.filter(student=profile).exclude(status__in=['accepted', 'closed', 'rejected', 'withdrawn']).count()
        matches_count = Match.objects.filter(student=profile, status__in=['active', 'hired']).count()

        # Recommended Jobs (Active job postings that the student hasn't swiped on yet)
        swiped_job_ids = Swipe.objects.filter(student=profile).values_list('job_id', flat=True)
        recommended_jobs = JobPosting.objects.filter(status='active').exclude(id__in=swiped_job_ids)[:5]

        # Recent Earnings
        recent_earnings = Earning.objects.filter(student=profile).order_by('-created_at')[:5]

        context.update({
            'profile': profile,
            'completed_shifts': completed_shifts,
            'total_earnings': total_earnings,
            'active_applications_count': active_apps,
            'matches_count': matches_count,
            'recommended_jobs': recommended_jobs,
            'recent_earnings': recent_earnings,
            'unread_notifications_count': Notification.objects.filter(user=self.request.user, is_read=False).count(),
        })
        return context


class StudentProfileEditView(StudentRequiredMixin, View):
    template_name = 'students/profile.html'

    def get(self, request):
        profile = get_object_or_404(StudentProfile, user=request.user)
        form = StudentProfileForm(instance=profile)
        skills = StudentSkill.objects.filter(student=profile)
        all_skills = Skill.objects.all()
        return render(request, self.template_name, {
            'form': form,
            'profile': profile,
            'skills': skills,
            'all_skills': all_skills
        })

    def post(self, request):
        profile = get_object_or_404(StudentProfile, user=request.user)
        form = StudentProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('student_profile_edit')
        
        skills = StudentSkill.objects.filter(student=profile)
        all_skills = Skill.objects.all()
        return render(request, self.template_name, {
            'form': form,
            'profile': profile,
            'skills': skills,
            'all_skills': all_skills
        })


class SwipeConsoleView(StudentRequiredMixin, TemplateView):
    template_name = 'students/swipe.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = get_object_or_404(StudentProfile, user=self.request.user)
        
        # Pull active jobs the student hasn't swiped on yet
        swiped_ids = Swipe.objects.filter(student=profile).values_list('job_id', flat=True)
        jobs = JobPosting.objects.filter(status='active').exclude(id__in=swiped_ids).prefetch_related('required_skills__skill')
        
        context.update({
            'profile': profile,
            'jobs': jobs,
        })
        return context


class SwipeActionView(StudentRequiredMixin, View):
    """
    Ajax endpoint handling swipe actions (like/dislike).
    Returns JSON.
    """
    def post(self, request, *args, **kwargs):
        job_id = request.POST.get('job_id')
        direction = request.POST.get('direction')
        
        if direction not in ['like', 'dislike', 'save']:
            return JsonResponse({'error': 'Invalid swipe direction'}, status=400)
            
        profile = get_object_or_404(StudentProfile, user=request.user)
        job = get_object_or_404(JobPosting, id=job_id)
        
        with transaction.atomic():
            # Create Swipe record
            swipe, created = Swipe.objects.get_or_create(
                student=profile,
                job=job,
                defaults={'direction': direction}
            )
            
            if not created:
                return JsonResponse({'message': 'Already swiped on this job'}, status=200)

            # Create application if student liked the job
            if direction == 'like':
                JobApplication.objects.get_or_create(
                    student=profile,
                    job=job,
                    defaults={'status': 'applied'}
                )
        
        return JsonResponse({
            'success': True,
            'matched': False,
            'match_details': None
        })


class ApplicationsListView(StudentRequiredMixin, ListView):
    template_name = 'students/applications.html'
    context_object_name = 'applications'

    def get_queryset(self):
        profile = get_object_or_404(StudentProfile, user=self.request.user)
        return JobApplication.objects.filter(student=profile).select_related('job__business').order_by('-created_at')


class EarningsListView(StudentRequiredMixin, TemplateView):
    template_name = 'students/earnings.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = get_object_or_404(StudentProfile, user=self.request.user)
        
        # Calculate payment metrics
        released_earnings = Earning.objects.filter(student=profile, payment_status='released')
        escrow_earnings = Earning.objects.filter(student=profile, payment_status='escrow')
        
        total_earned = sum(e.net_amount for e in released_earnings)
        total_escrow = sum(e.net_amount for e in escrow_earnings)
        
        all_earnings = Earning.objects.filter(student=profile).select_related('job__business').order_by('-created_at')
        
        context.update({
            'total_earned': total_earned,
            'total_escrow': total_escrow,
            'earnings_logs': all_earnings,
        })
        return context


class NotificationsListView(StudentRequiredMixin, ListView):
    template_name = 'students/notifications.html'
    context_object_name = 'notifications'

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')


class MarkNotificationsReadView(StudentRequiredMixin, View):
    """
    Ajax view to mark all unread notifications as read.
    """
    def post(self, request, *args, **kwargs):
        Notification.objects.filter(user=request.user, is_read=False).update(
            is_read=True,
            read_at=timezone.now()
        )
        return JsonResponse({'success': True})


class StudentProfileView(drf_generics.RetrieveUpdateAPIView):
    """
    Retrieve or Update details of the authenticated student's profile.
    Requires student role permissions. Used for JWT-based DRF tests.
    """
    serializer_class = StudentProfileSerializer
    permission_classes = [IsAuthenticated, IsStudent]

    def get_object(self):
        return StudentProfile.objects.get(user=self.request.user)
