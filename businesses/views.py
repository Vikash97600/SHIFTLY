import datetime
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import TemplateView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.db import transaction
from django.utils import timezone
from django.contrib import messages

# DRF Imports for backwards compatibility
from rest_framework import generics as drf_generics
from rest_framework.permissions import IsAuthenticated
from accounts.permissions import IsBusiness
from .serializers import BusinessProfileSerializer

from .models import BusinessProfile, Earning
from .forms import BusinessProfileForm
from jobs.models import JobPosting
from swipes.models import Swipe
from matches.models import Match, JobApplication
from notifications.models import Notification
from ratings.models import RatingReview
from ratings.forms import RatingReviewForm
from django.contrib.auth import get_user_model

User = get_user_model()

class BusinessRequiredMixin(LoginRequiredMixin):
    """
    Mixin that ensures the user is logged in and possesses the 'business' role.
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.role != 'business' or not request.user.is_active or request.user.status != User.AccountStatus.APPROVED:
            raise PermissionDenied("Only approved businesses can access this area.")
        return super().dispatch(request, *args, **kwargs)


class BusinessDashboardView(BusinessRequiredMixin, TemplateView):
    template_name = 'businesses/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = get_object_or_404(BusinessProfile, user=self.request.user)

        # Statistics
        total_jobs = JobPosting.objects.filter(business=profile).count()
        active_jobs = JobPosting.objects.filter(business=profile, status='active').count()
        filled_slots = sum(job.slots_filled for job in JobPosting.objects.filter(business=profile))
        
        # Calculate platform spending (Released + Escrowed payments)
        all_payments = Earning.objects.filter(business=profile)
        total_spent = sum(p.gross_amount for p in all_payments.filter(payment_status='released'))
        escrow_held = sum(p.gross_amount for p in all_payments.filter(payment_status='escrow'))

        # Recent applications (Matching applicants who swiped 'like')
        recent_applications = JobApplication.objects.filter(job__business=profile).order_by('-created_at')[:5]

        # Active jobs overview
        jobs_overview = JobPosting.objects.filter(business=profile).order_by('-created_at')[:5]

        context.update({
            'profile': profile,
            'total_jobs_posted': total_jobs,
            'active_jobs_count': active_jobs,
            'filled_slots_count': filled_slots,
            'total_spent': total_spent,
            'escrow_held': escrow_held,
            'recent_applications': recent_applications,
            'jobs_overview': jobs_overview,
            'unread_notifications_count': Notification.objects.filter(user=self.request.user, is_read=False).count(),
        })
        return context


class BusinessProfileEditView(BusinessRequiredMixin, View):
    template_name = 'businesses/profile.html'

    def get(self, request):
        profile = get_object_or_404(BusinessProfile, user=request.user)
        form = BusinessProfileForm(instance=profile)
        return render(request, self.template_name, {
            'form': form,
            'profile': profile
        })

    def post(self, request):
        profile = get_object_or_404(BusinessProfile, user=request.user)
        form = BusinessProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Company profile updated successfully.")
            return redirect('business_profile_edit')
        
        return render(request, self.template_name, {
            'form': form,
            'profile': profile
        })


class ApplicantManageView(BusinessRequiredMixin, ListView):
    template_name = 'businesses/applicants.html'
    context_object_name = 'applications'

    def get_queryset(self):
        profile = get_object_or_404(BusinessProfile, user=self.request.user)
        queryset = JobApplication.objects.filter(job__business=profile).select_related('student', 'job').order_by('-created_at')
        job_id = self.request.GET.get('job_id')
        if job_id:
            queryset = queryset.filter(job_id=job_id)
        return queryset


class HireActionView(BusinessRequiredMixin, View):
    """
    Ajax View to approve an application.
    Changes application status to accepted, match to hired, 
    increments slots filled, creates an Earning, and locks escrow.
    """
    def post(self, request, *args, **kwargs):
        application_id = request.POST.get('application_id')
        application = get_object_or_404(JobApplication, id=application_id)
        
        # Verify ownership
        profile = get_object_or_404(BusinessProfile, user=request.user)
        if application.job.business != profile:
            return JsonResponse({'error': 'Unauthorized'}, status=403)

        if application.status == 'accepted':
            return JsonResponse({'message': 'Applicant already hired for this shift'}, status=200)

        job = application.job
        if job.slots_filled >= job.slots_available:
            return JsonResponse({'error': 'No available slots left on this shift'}, status=400)

        with transaction.atomic():
            # Create or update Match record
            match, created = Match.objects.update_or_create(
                student=application.student,
                job=job,
                defaults={'status': 'hired'}
            )

            # Update Application and Match Link
            application.status = 'accepted'
            application.match = match
            application.save()

            # Increment slots filled
            job.slots_filled += 1
            if job.slots_filled >= job.slots_available:
                job.status = 'filled'
            job.save()

            # Calculate Earnings Ledger (Escrow)
            duration_hours = 8.0
            if job.shift_start_time and job.shift_end_time:
                start_delta = datetime.timedelta(hours=job.shift_start_time.hour, minutes=job.shift_start_time.minute)
                end_delta = datetime.timedelta(hours=job.shift_end_time.hour, minutes=job.shift_end_time.minute)
                if end_delta > start_delta:
                    duration_hours = (end_delta - start_delta).total_seconds() / 3600.0
                else:
                    duration_hours = (end_delta + datetime.timedelta(days=1) - start_delta).total_seconds() / 3600.0

            gross = job.base_pay * Decimal(duration_hours)
            fee = gross * Decimal('0.10')
            net = gross - fee

            txn_ref = f"TXN-{match.uuid.hex[:8].upper()}"
            Earning.objects.create(
                student=application.student,
                business=profile,
                job=job,
                gross_amount=gross,
                platform_fee=fee,
                net_amount=net,
                payment_status='escrow',
                transaction_reference=txn_ref
            )

            # Send Match Notification to Student User
            Notification.objects.create(
                user=application.student.user,
                type='match',
                title="It's a Shift Match!",
                body=f"You have matched with '{job.title}' at {profile.company_name}."
            )

            # Send Payment Escrow Notification to Student User
            Notification.objects.create(
                user=application.student.user,
                type='payment',
                title="Payout Escrow Locked",
                body=f"Payout for '{job.title}' at {profile.company_name} is locked in escrow."
            )

        return JsonResponse({
            'success': True,
            'status': 'accepted',
            'net_payout': float(net)
        })


class SubmitRatingView(BusinessRequiredMixin, View):
    """
    Form view for rating students after completing a shift.
    """
    template_name = 'businesses/rate-student.html'

    def get(self, request, application_id):
        application = get_object_or_404(JobApplication, id=application_id)
        form = RatingReviewForm()
        return render(request, self.template_name, {
            'form': form,
            'application': application
        })

    def post(self, request, application_id):
        application = get_object_or_404(JobApplication, id=application_id)
        form = RatingReviewForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                review = form.save(commit=False)
                review.match = application.match
                review.reviewer = request.user
                review.reviewee = application.student.user
                review.save()

                # Update student profile average reputation score
                student = application.student
                all_reviews = RatingReview.objects.filter(reviewee=student.user)
                avg_rating = sum(r.rating for r in all_reviews) / all_reviews.count()
                
                # Convert rating scale (1-5) to reputation score (1-100)
                student.reputation_score = Decimal(avg_rating * 20)
                student.save()

                # Release Escrow Payout to released
                earning = Earning.objects.filter(student=student, job=application.job, payment_status='escrow').first()
                if earning:
                    earning.payment_status = 'released'
                    earning.save()

                messages.success(request, f"Review submitted. Payout released to {student.first_name}!")
                return redirect('business_applicants')

        return render(request, self.template_name, {
            'form': form,
            'application': application
        })


# =========================================================================
# DRF VIEW (JWT Authenticated REST API for backwards compatibility)
# =========================================================================
class BusinessProfileView(drf_generics.RetrieveUpdateAPIView):
    """
    Retrieve or Update details of the authenticated business owner's profile.
    Requires business owner role permissions. Used for JWT API tests.
    """
    serializer_class = BusinessProfileSerializer
    permission_classes = [IsAuthenticated, IsBusiness]

    def get_object(self):
        return BusinessProfile.objects.get(user=self.request.user)
