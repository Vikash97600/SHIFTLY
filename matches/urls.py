from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MatchViewSet, StudentMatchesView, BusinessMatchesView

router = DefaultRouter()
router.register(r'list', MatchViewSet, basename='match')

urlpatterns = [
    # DRF API ViewSet prefix
    path('api/', include(router.urls)),
    
    # Template dashboard views
    path('student/dashboard/', StudentMatchesView.as_view(), name='student_matches'),
    path('business/dashboard/', BusinessMatchesView.as_view(), name='business_matches'),
]
