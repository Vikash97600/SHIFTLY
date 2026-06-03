"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from accounts.views import (
    LandingPageView, LoginPageView, RegisterPageView,
    AboutPageView, ContactPageView, LogoutPageView
)

urlpatterns = [
    path("", LandingPageView.as_view(), name="landing"),
    path("login/", LoginPageView.as_view(), name="login_page"),
    path("register/", RegisterPageView.as_view(), name="register_page"),
    path("about/", AboutPageView.as_view(), name="about_page"),
    path("contact/", ContactPageView.as_view(), name="contact_page"),
    path("logout/", LogoutPageView.as_view(), name="logout_page"),

    path("admin/", admin.site.urls),
    path("api/v1/accounts/", include("accounts.urls")),
    path("api/v1/students/", include("students.urls")),
    path("api/v1/businesses/", include("businesses.urls")),
    path("api/v1/jobs/", include("jobs.urls")),
    path("api/v1/matches/", include("matches.urls")),
    path("api/v1/chat/", include("chat.urls")),
    path("api/v1/adminpanel/", include("adminpanel.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

