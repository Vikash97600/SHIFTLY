from django.urls import path
from .views import JobPostView, JobManageView, JobStatusUpdateView

urlpatterns = [
    path('post/', JobPostView.as_view(), name='job_post'),
    path('manage/', JobManageView.as_view(), name='job_management'),
    path('manage/<int:job_id>/status/', JobStatusUpdateView.as_view(), name='job_status_update'),
]
