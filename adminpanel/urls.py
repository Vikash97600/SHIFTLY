from django.urls import path
from .views import (
    AdminDashboardView, AdminUsersView, AdminBusinessesView, AdminJobsView,
    AdminVerificationsView, AdminReportsView, AdminToggleUserActiveView,
    AdminVerifyRequestActionView, AdminJobModerationActionView, AdminReportResolveActionView
)

urlpatterns = [
    path('dashboard/', AdminDashboardView.as_view(), name='admin_dashboard'),
    path('users/', AdminUsersView.as_view(), name='admin_users'),
    path('businesses/', AdminBusinessesView.as_view(), name='admin_businesses'),
    path('jobs/', AdminJobsView.as_view(), name='admin_jobs'),
    path('verifications/', AdminVerificationsView.as_view(), name='admin_verifications'),
    path('reports/', AdminReportsView.as_view(), name='admin_reports'),
    
    # AJAX Moderation Actions
    path('users/toggle/<int:user_id>/', AdminToggleUserActiveView.as_view(), name='admin_toggle_user'),
    path('verifications/action/<int:request_id>/', AdminVerifyRequestActionView.as_view(), name='admin_verification_action'),
    path('jobs/action/<int:job_id>/', AdminJobModerationActionView.as_view(), name='admin_job_action'),
    path('reports/action/<int:report_id>/', AdminReportResolveActionView.as_view(), name='admin_report_action'),
]
