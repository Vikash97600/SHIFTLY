from django.urls import path
from .views import (
    BusinessDashboardView,
    BusinessProfileEditView,
    BusinessProfileView,
    ApplicantManageView,
    HireActionView,
    SubmitRatingView
)

urlpatterns = [
    path('dashboard/', BusinessDashboardView.as_view(), name='business_dashboard'),
    path('profile/', BusinessProfileView.as_view(), name='business_profile'),
    path('profile/edit/', BusinessProfileEditView.as_view(), name='business_profile_edit'),
    path('applicants/', ApplicantManageView.as_view(), name='business_applicants'),
    path('applicants/hire/', HireActionView.as_view(), name='business_hire_action'),
    path('applicants/rate/<int:application_id>/', SubmitRatingView.as_view(), name='business_rate_student'),
]
