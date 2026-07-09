from django.urls import path
from .views import JobPostView, JobManageView, JobStatusUpdateView, JobEditView, JobDeleteView

urlpatterns = [
    path('post/', JobPostView.as_view(), name='job_post'),
    path('manage/', JobManageView.as_view(), name='job_management'),
    path('manage/<int:job_id>/status/', JobStatusUpdateView.as_view(), name='job_status_update'),
    path('manage/<int:job_id>/edit/', JobEditView.as_view(), name='job_edit'),
    path('manage/<int:job_id>/delete/', JobDeleteView.as_view(), name='job_delete'),
]
