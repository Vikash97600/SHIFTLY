from django.urls import path
from .views import (
    StudentDashboardView,
    StudentProfileEditView,
    StudentProfileView,
    SwipeConsoleView,
    SwipeActionView,
    ApplicationsListView,
    EarningsListView,
    NotificationsListView,
    MarkNotificationsReadView,
    SubmitBusinessRatingView,
    AddStudentSkillView,
    RemoveStudentSkillView,
)

urlpatterns = [
    path('dashboard/', StudentDashboardView.as_view(), name='student_dashboard'),
    path('profile/', StudentProfileView.as_view(), name='student_profile'),
    path('profile/edit/', StudentProfileEditView.as_view(), name='student_profile_edit'),
    path('swipe/', SwipeConsoleView.as_view(), name='student_swipe'),
    path('swipe/action/', SwipeActionView.as_view(), name='student_swipe_action'),
    path('applications/', ApplicationsListView.as_view(), name='student_applications'),
    path('earnings/', EarningsListView.as_view(), name='student_earnings'),
    path('rate/<int:match_id>/', SubmitBusinessRatingView.as_view(), name='student_rate_business'),
    path('notifications/', NotificationsListView.as_view(), name='student_notifications'),
    path('notifications/read/', MarkNotificationsReadView.as_view(), name='student_notifications_read'),
    path('skills/add/', AddStudentSkillView.as_view(), name='student_skill_add'),
    path('skills/remove/<int:pk>/', RemoveStudentSkillView.as_view(), name='student_skill_remove'),
]
