from django.urls import path
from .views import JobPostView, JobManageView

urlpatterns = [
    path('post/', JobPostView.as_view(), name='job_post'),
    path('manage/', JobManageView.as_view(), name='job_management'),
]
