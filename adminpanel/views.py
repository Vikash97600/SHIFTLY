import json
import datetime
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import TemplateView, ListView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse, HttpResponseForbidden
from django.db.models import Sum, Q
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib import messages

from accounts.models import Verification, ReputationLog
from businesses.models import BusinessProfile, Earning
from students.models import StudentProfile
from jobs.models import JobPosting
from matches.models import Match, JobApplication
from reports.models import Report
from .models import AuditLog

User = get_user_model()

class AdminRequiredMixin(LoginRequiredMixin):
    """
    Mixin that ensures the user is logged in and has the 'admin' role.
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.role != 'admin':
            raise PermissionDenied("Only administrators can access this area.")
        return super().dispatch(request, *args, **kwargs)


class AdminDashboardView(AdminRequiredMixin, TemplateView):
    template_name = 'adminpanel/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 1. KPI Calculations
        total_users = User.objects.count()
        active_jobs = JobPosting.objects.filter(status='active').count()
        total_businesses = BusinessProfile.objects.count()
        total_matches = Match.objects.count()
        total_revenue = Earning.objects.aggregate(sum=Sum('platform_fee'))['sum'] or Decimal('0.00')

        # 2. Charts Aggregation
        today = timezone.now().date()
        
        # Chart 1: Revenue Trends (Last 7 Days)
        revenue_labels = []
        revenue_values = []
        for i in range(6, -1, -1):
            day = today - datetime.timedelta(days=i)
            day_fees = Earning.objects.filter(created_at__date=day).aggregate(sum=Sum('platform_fee'))['sum'] or Decimal('0.00')
            revenue_labels.append(day.strftime('%b %d'))
            revenue_values.append(float(day_fees))

        # Chart 2: User Signups Growth (Last 7 Days)
        signup_labels = []
        signup_values = []
        for i in range(6, -1, -1):
            day = today - datetime.timedelta(days=i)
            day_signups = User.objects.filter(date_joined__date=day).count()
            signup_labels.append(day.strftime('%b %d'))
            signup_values.append(day_signups)

        # Chart 3: User Role Distribution
        student_count = User.objects.filter(role='student').count()
        business_count = User.objects.filter(role='business').count()
        admin_count = User.objects.filter(role='admin').count()

        # Chart 4: Matching Pipeline
        total_apps = JobApplication.objects.count()
        filled_shifts = JobPosting.objects.filter(status='filled').count()

        context.update({
            # KPIs
            'total_users': total_users,
            'active_jobs': active_jobs,
            'total_businesses': total_businesses,
            'total_matches': total_matches,
            'total_revenue': total_revenue,
            
            # Chart Data
            'revenue_labels': json.dumps(revenue_labels),
            'revenue_values': json.dumps(revenue_values),
            'signup_labels': json.dumps(signup_labels),
            'signup_values': json.dumps(signup_values),
            'student_count': student_count,
            'business_count': business_count,
            'admin_count': admin_count,
            'total_apps': total_apps,
            'filled_shifts': filled_shifts,

            # Audit Logs
            'recent_logs': AuditLog.objects.select_related('actor').order_by('-created_at')[:8],
        })
        return context


class AdminUsersView(AdminRequiredMixin, ListView):
    template_name = 'adminpanel/users.html'
    context_object_name = 'users'
    paginate_by = 25

    def get_queryset(self):
        queryset = User.objects.all().order_by('-date_joined')
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(Q(email__icontains=query) | Q(role__icontains=query))
        return queryset


class AdminBusinessesView(AdminRequiredMixin, ListView):
    template_name = 'adminpanel/businesses.html'
    context_object_name = 'businesses'
    paginate_by = 25

    def get_queryset(self):
        return BusinessProfile.objects.select_related('user').order_by('-created_at')


class AdminJobsView(AdminRequiredMixin, ListView):
    template_name = 'adminpanel/jobs.html'
    context_object_name = 'jobs'
    paginate_by = 25

    def get_queryset(self):
        return JobPosting.objects.select_related('business').order_by('-created_at')


class AdminVerificationsView(AdminRequiredMixin, ListView):
    template_name = 'adminpanel/verifications.html'
    context_object_name = 'requests'
    paginate_by = 25

    def get_queryset(self):
        return Verification.objects.select_related('user').order_by('-submitted_at')


class AdminReportsView(AdminRequiredMixin, ListView):
    template_name = 'adminpanel/reports.html'
    context_object_name = 'reports'
    paginate_by = 25

    def get_queryset(self):
        return Report.objects.select_related('reporter', 'reported_user', 'reported_job').order_by('-created_at')


# =========================================================================
# AJAX Moderation Actions View Handler API
# =========================================================================

class AdminToggleUserActiveView(AdminRequiredMixin, View):
    def post(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        if user == request.user:
            return JsonResponse({'error': 'Cannot suspend yourself'}, status=400)

        user.is_active = not user.is_active
        user.save()

        # Audit logging
        AuditLog.objects.create(
            actor=request.user,
            action='toggle_user_status',
            target_table='accounts_user',
            target_id=user.id,
            details={'email': user.email, 'is_active': user.is_active}
        )

        return JsonResponse({'success': True, 'is_active': user.is_active})


class AdminVerifyRequestActionView(AdminRequiredMixin, View):
    def post(self, request, request_id):
        verification = get_object_or_404(Verification, id=request_id)
        action_status = request.POST.get('status')
        reason = request.POST.get('reason', '')

        if action_status not in ['approved', 'rejected']:
            return JsonResponse({'error': 'Invalid verification status'}, status=400)

        verification.status = action_status
        verification.reviewer = request.user
        verification.rejection_reason = reason if action_status == 'rejected' else ''
        verification.reviewed_at = timezone.now()
        verification.save()

        # If it is a business user, update the BusinessProfile verification_status
        if hasattr(verification.user, 'business_profile'):
            profile = verification.user.business_profile
            profile.verification_status = 'verified' if action_status == 'approved' else 'rejected'
            profile.save()

        # Audit logging
        AuditLog.objects.create(
            actor=request.user,
            action=f'verification_{action_status}',
            target_table='accounts_verification',
            target_id=verification.id,
            details={'user_email': verification.user.email, 'reason': reason}
        )

        return JsonResponse({'success': True, 'status': action_status})


class AdminJobModerationActionView(AdminRequiredMixin, View):
    def post(self, request, job_id):
        job = get_object_or_404(JobPosting, id=job_id)
        action = request.POST.get('action') # delete, restore

        if action == 'delete':
            job.status = 'deleted'
        elif action == 'restore':
            job.status = 'active'
        else:
            return JsonResponse({'error': 'Invalid moderation action'}, status=400)
        
        job.save()

        # Audit logging
        AuditLog.objects.create(
            actor=request.user,
            action=f'job_{action}',
            target_table='jobs_jobposting',
            target_id=job.id,
            details={'title': job.title, 'business': job.business.company_name}
        )

        return JsonResponse({'success': True, 'status': job.status})


class AdminReportResolveActionView(AdminRequiredMixin, View):
    def post(self, request, report_id):
        report = get_object_or_404(Report, id=report_id)
        action = request.POST.get('action') # resolve, dismiss
        resolution_notes = request.POST.get('notes', '')

        if action == 'resolve':
            report.status = Report.ReportStatus.RESOLVED
        elif action == 'dismiss':
            report.status = Report.ReportStatus.DISMISSED
        else:
            return JsonResponse({'error': 'Invalid report action'}, status=400)

        report.resolver = request.user
        report.resolution_action = resolution_notes
        report.save()

        # Audit logging
        AuditLog.objects.create(
            actor=request.user,
            action=f'report_{action}',
            target_table='reports_report',
            target_id=report.id,
            details={'reporter': report.reporter.email, 'notes': resolution_notes}
        )

        return JsonResponse({'success': True, 'status': report.status})
