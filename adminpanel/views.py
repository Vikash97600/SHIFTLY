import json
import datetime
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import TemplateView, ListView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse
from django.db.models import Sum, Q
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib import messages

from accounts.models import Verification, ReputationLog
from accounts.utils import create_account_decision_notification
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

        pending_businesses = BusinessProfile.objects.filter(user__status='pending').select_related('user').order_by('-created_at')

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
            'pending_businesses': pending_businesses,
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


class AdminBusinessApprovalActionView(AdminRequiredMixin, View):
    def post(self, request, business_id):
        profile = get_object_or_404(BusinessProfile, id=business_id)
        action = request.POST.get('action')
        reason = request.POST.get('reason', '').strip()

        if action not in ['approve', 'reject']:
            return JsonResponse({'error': 'Invalid action'}, status=400)

        user = profile.user
        if action == 'approve':
            user.status = User.AccountStatus.APPROVED
            user.is_active = True
            user.is_verified = True
            user.approved_by = request.user
            user.approved_at = timezone.now()
            user.save(update_fields=['status', 'is_active', 'is_verified', 'approved_by', 'approved_at', 'updated_at'])

            profile.status = 'APPROVED'
            profile.verification_status = 'verified'
            profile.is_verified = True
            profile.is_active = True
            profile.approved_by = request.user
            profile.approved_at = timezone.now()
            profile.rejection_reason = ""
            profile.verification_updated_at = timezone.now()
            profile.save()

            Verification.objects.filter(user=user, status='pending').update(
                status='approved',
                reviewer=request.user,
                reviewed_at=timezone.now(),
                rejection_reason=''
            )

            create_account_decision_notification(user, True)
        else:
            user.status = User.AccountStatus.REJECTED
            user.is_active = False
            user.is_verified = False
            user.save(update_fields=['status', 'is_active', 'is_verified', 'updated_at'])

            profile.status = 'REJECTED'
            profile.verification_status = 'rejected'
            profile.is_verified = False
            profile.is_active = False
            profile.approved_by = request.user
            profile.approved_at = timezone.now()
            profile.rejection_reason = reason
            profile.verification_updated_at = timezone.now()
            profile.save()

            Verification.objects.filter(user=user, status='pending').update(
                status='rejected',
                reviewer=request.user,
                reviewed_at=timezone.now(),
                rejection_reason=reason
            )

            create_account_decision_notification(user, False, reason)

        AuditLog.objects.create(
            actor=request.user,
            action=f'business_{action}',
            target_table='businesses_businessprofile',
            target_id=profile.id,
            details={'business': profile.company_name, 'reason': reason},
        )

        return JsonResponse({'success': True, 'status': profile.status})


class AdminJobsView(AdminRequiredMixin, ListView):
    template_name = 'adminpanel/jobs.html'
    context_object_name = 'jobs'
    paginate_by = 25

    def get_queryset(self):
        return JobPosting.objects.select_related('business').order_by('-created_at')


class AdminVerificationsView(AdminRequiredMixin, ListView):
    template_name = 'adminpanel/verifications.html'
    context_object_name = 'businesses'
    paginate_by = 25

    def get_queryset(self):
        queryset = BusinessProfile.objects.select_related('user', 'approved_by').all()

        search_query = self.request.GET.get('search', '').strip()
        if search_query:
            queryset = queryset.filter(
                Q(company_name__icontains=search_query) |
                Q(owner_name__icontains=search_query) |
                Q(user__email__icontains=search_query) |
                Q(mobile_number__icontains=search_query) |
                Q(business_category__icontains=search_query)
            )

        filter_type = self.request.GET.get('filter', '').strip()
        active_tab = self.request.GET.get('tab', 'pending').lower()
        if active_tab not in ['pending', 'approved', 'rejected']:
            active_tab = 'pending'

        if filter_type == 'pending':
            queryset = queryset.filter(status='PENDING')
        elif filter_type == 'approved':
            queryset = queryset.filter(status='APPROVED')
        elif filter_type == 'rejected':
            queryset = queryset.filter(status='REJECTED')
        elif filter_type == 'documents_missing':
            queryset = queryset.filter(
                Q(business_license='') | Q(business_license__isnull=True) |
                Q(gst_document='') | Q(gst_document__isnull=True) |
                Q(tax_document='') | Q(tax_document__isnull=True)
            )
        else:
            queryset = queryset.filter(status=active_tab.upper())

        sort_by = self.request.GET.get('sort', '').strip()
        if sort_by == 'oldest_pending':
            queryset = queryset.order_by('created_at')
        elif sort_by == 'newest_requests':
            queryset = queryset.order_by('-created_at')
        elif sort_by == 'recently_registered':
            queryset = queryset.order_by('-created_at')
        else:
            queryset = queryset.order_by('-created_at')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        pending_count = BusinessProfile.objects.filter(status='PENDING').count()
        today = timezone.now().date()
        approved_today_count = BusinessProfile.objects.filter(status='APPROVED', approved_at__date=today).count()
        
        rejected_today = BusinessProfile.objects.filter(status='REJECTED', verification_updated_at__date=today).count()
        rejected_week = BusinessProfile.objects.filter(status='REJECTED', verification_updated_at__gte=timezone.now() - datetime.timedelta(days=7)).count()
        rejected_month = BusinessProfile.objects.filter(status='REJECTED', verification_updated_at__gte=timezone.now() - datetime.timedelta(days=30)).count()
        rejected_all_time = BusinessProfile.objects.filter(status='REJECTED').count()
        
        pending_businesses = BusinessProfile.objects.filter(status='PENDING')
        docs_awaiting_review = 0
        for biz in pending_businesses:
            if biz.business_license:
                docs_awaiting_review += 1
            if biz.gst_document:
                docs_awaiting_review += 1
            if biz.tax_document:
                docs_awaiting_review += 1

        approved_businesses = BusinessProfile.objects.filter(status='APPROVED', approved_at__isnull=False, verification_requested_at__isnull=False)
        total_approved = approved_businesses.count()
        if total_approved > 0:
            durations = []
            for b in approved_businesses:
                durations.append(b.approved_at - b.verification_requested_at)
            total_duration = sum(durations, datetime.timedelta())
            avg_duration = total_duration / total_approved
            
            days = avg_duration.days
            hours, remainder = divmod(avg_duration.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            
            if days > 0:
                avg_time_str = f"{days} Day{'s' if days > 1 else ''} {hours} Hour{'s' if hours != 1 else ''}"
            elif hours > 0:
                avg_time_str = f"{hours} Hour{'s' if hours != 1 else ''} {minutes} Minute{'s' if minutes != 1 else ''}"
            else:
                avg_time_str = f"{minutes} Minute{'s' if minutes != 1 else ''}"
        else:
            avg_time_str = "N/A"

        verified_count = BusinessProfile.objects.filter(status='APPROVED').count()

        active_tab = self.request.GET.get('tab', 'pending').lower()
        if active_tab not in ['pending', 'approved', 'rejected']:
            active_tab = 'pending'

        context.update({
            'pending_count': pending_count,
            'approved_today_count': approved_today_count,
            'rejected_today': rejected_today,
            'rejected_week': rejected_week,
            'rejected_month': rejected_month,
            'rejected_all_time': rejected_all_time,
            'docs_awaiting_review': docs_awaiting_review,
            'avg_time_str': avg_time_str,
            'verified_count': verified_count,
            'active_tab': active_tab,
            'search_query': self.request.GET.get('search', ''),
            'filter_type': self.request.GET.get('filter', ''),
            'sort_by': self.request.GET.get('sort', ''),
        })
        return context


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

        if hasattr(verification.user, 'business_profile'):
            profile = verification.user.business_profile
            user = verification.user
            
            if action_status == 'approved':
                user.status = User.AccountStatus.APPROVED
                user.is_active = True
                user.is_verified = True
                user.approved_by = request.user
                user.approved_at = timezone.now()
                user.save(update_fields=['status', 'is_active', 'is_verified', 'approved_by', 'approved_at', 'updated_at'])

                profile.status = 'APPROVED'
                profile.verification_status = 'verified'
                profile.is_verified = True
                profile.is_active = True
                profile.approved_by = request.user
                profile.approved_at = timezone.now()
                profile.rejection_reason = ""
                profile.verification_updated_at = timezone.now()
                profile.save()

                create_account_decision_notification(user, True)
            else:
                user.status = User.AccountStatus.REJECTED
                user.is_active = False
                user.is_verified = False
                user.save(update_fields=['status', 'is_active', 'is_verified', 'updated_at'])

                profile.status = 'REJECTED'
                profile.verification_status = 'rejected'
                profile.is_verified = False
                profile.is_active = False
                profile.approved_by = request.user
                profile.approved_at = timezone.now()
                profile.rejection_reason = reason
                profile.verification_updated_at = timezone.now()
                profile.save()

                create_account_decision_notification(user, False, reason)

        AuditLog.objects.create(
            actor=request.user,
            action=f'verification_{action_status}',
            target_table='accounts_verification',
            target_id=verification.id,
            details={'user_email': verification.user.email, 'reason': reason}
        )

        return JsonResponse({'success': True, 'status': action_status})


class AdminExportVerificationsCSVView(AdminRequiredMixin, View):
    def get(self, request):
        import csv
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="verifications_report.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Business Name', 'Owner Name', 'Email', 'Mobile', 
            'Business Category', 'Address', 'Status', 
            'Registered At', 'Verified At', 'Approved By', 'Rejection Reason'
        ])
        
        businesses = BusinessProfile.objects.select_related('user', 'approved_by').all().order_by('-created_at')
        for biz in businesses:
            writer.writerow([
                biz.company_name,
                biz.owner_name or '',
                biz.user.email,
                biz.mobile_number or '',
                biz.business_category or '',
                biz.address or '',
                biz.status,
                biz.created_at.strftime('%Y-%m-%d %H:%M:%S') if biz.created_at else '',
                biz.approved_at.strftime('%Y-%m-%d %H:%M:%S') if biz.approved_at else '',
                biz.approved_by.email if biz.approved_by else '',
                biz.rejection_reason or ''
            ])
            
        return response


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


from django.db.models import Avg
from ratings.models import (
    StudentReputation, StudentReputationHistory,
    BusinessReputation, BusinessReputationHistory
)
from ratings.services import recalculate_student_reputation, recalculate_business_reputation

class AdminReputationView(AdminRequiredMixin, TemplateView):
    template_name = 'adminpanel/reputation.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 1. KPIs
        avg_student_score = StudentProfile.objects.aggregate(avg=Avg('reputation_score'))['avg'] or 100.0
        avg_business_score = BusinessProfile.objects.aggregate(avg=Avg('reputation_score'))['avg'] or 100.0
        suspicious_student_count = StudentProfile.objects.filter(reputation_score__lt=60).count()
        suspicious_business_count = BusinessProfile.objects.filter(reputation_score__lt=60).count()
        
        # 2. Top & Bottom Lists
        highest_students = StudentProfile.objects.select_related('reputation').order_by('-reputation_score')[:5]
        lowest_students = StudentProfile.objects.select_related('reputation').order_by('reputation_score')[:5]
        highest_businesses = BusinessProfile.objects.select_related('reputation').order_by('-reputation_score')[:5]
        lowest_businesses = BusinessProfile.objects.select_related('reputation').order_by('reputation_score')[:5]
        
        # 3. Suspicious Accounts
        suspicious_students = StudentProfile.objects.filter(reputation_score__lt=60).select_related('reputation')
        suspicious_businesses = BusinessProfile.objects.filter(reputation_score__lt=60).select_related('reputation')
        
        # 4. History Logs
        student_history = StudentReputationHistory.objects.select_related('student').order_by('-created_at')[:15]
        business_history = BusinessReputationHistory.objects.select_related('business').order_by('-created_at')[:15]

        # 5. Load all users (for recalculation searchable selector)
        all_students = StudentProfile.objects.all().order_by('first_name')
        all_businesses = BusinessProfile.objects.all().order_by('company_name')

        context.update({
            'avg_student_score': avg_student_score,
            'avg_business_score': avg_business_score,
            'suspicious_count': suspicious_student_count + suspicious_business_count,
            'highest_students': highest_students,
            'lowest_students': lowest_students,
            'highest_businesses': highest_businesses,
            'lowest_businesses': lowest_businesses,
            'suspicious_students': suspicious_students,
            'suspicious_businesses': suspicious_businesses,
            'student_history': student_history,
            'business_history': business_history,
            'all_students': all_students,
            'all_businesses': all_businesses,
        })
        return context


class AdminRecalculateReputationActionView(AdminRequiredMixin, View):
    """
    POST View to trigger manual audit recalculation on a student or business owner's profile.
    """
    def post(self, request, *args, **kwargs):
        target_type = request.POST.get('target_type') # student or business
        target_id = request.POST.get('target_id')
        
        if not target_id:
            return JsonResponse({'error': 'Missing target ID'}, status=400)

        if target_type == 'student':
            profile = get_object_or_404(StudentProfile, id=target_id)
            recalculate_student_reputation(profile, reason=f"Manual Admin Recalculation by {request.user.email}")
            new_score = profile.reputation_score
        elif target_type == 'business':
            profile = get_object_or_404(BusinessProfile, id=target_id)
            recalculate_business_reputation(profile, reason=f"Manual Admin Recalculation by {request.user.email}")
            new_score = profile.reputation_score
        else:
            return JsonResponse({'error': 'Invalid target type'}, status=400)

        # Audit Log
        AuditLog.objects.create(
            actor=request.user,
            action='manual_recalculation',
            target_table='ratings_studentreputation' if target_type == 'student' else 'ratings_businessreputation',
            target_id=profile.id,
            details={'target_email': profile.user.email, 'new_score': float(new_score)}
        )

        return JsonResponse({'success': True, 'new_score': float(new_score)})
