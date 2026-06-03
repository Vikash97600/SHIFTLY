from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import get_user_model
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator

from .serializers import (
    RegisterSerializer,
    CustomTokenObtainPairSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer
)

User = get_user_model()

class CustomTokenObtainPairView(TokenObtainPairView):
    """
    JWT Login View returning access token, refresh token, and user metadata.
    """
    serializer_class = CustomTokenObtainPairSerializer


class RegisterView(generics.CreateAPIView):
    """
    Registers a new student or business owner user and initializes their profile record.
    """
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = (permissions.AllowAny,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({
            "message": "User registered successfully",
            "email": user.email,
            "role": user.role,
            "uuid": str(user.uuid)
        }, status=status.HTTP_201_CREATED)


class PasswordResetRequestView(APIView):
    """
    Accepts email address, validates existence, and simulates sending a password reset token.
    """
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        user = User.objects.get(email=email)

        # In production, we generate a reset link and send an email:
        # token = default_token_generator.make_token(user)
        # uid = urlsafe_base64_encode(force_bytes(user.pk))
        # send_mail(...)
        
        return Response({
            "message": "If this email is registered, a password reset link has been sent.",
            # returning mock tokens for testing/development integration:
            "development_token": default_token_generator.make_token(user),
            "development_uid": user.pk
        }, status=status.HTTP_200_OK)


class PasswordResetConfirmView(APIView):
    """
    Completes password reset confirming the token and user uid.
    """
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        password = serializer.validated_data['password']
        token = serializer.validated_data['token']
        uid = serializer.validated_data['uidb64']

        try:
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({"error": "Invalid user ID"}, status=status.HTTP_400_BAD_REQUEST)

        if not default_token_generator.check_token(user, token):
            return Response({"error": "Invalid or expired token"}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(password)
        user.save()
        return Response({"message": "Password reset successfully."}, status=status.HTTP_200_OK)


# =========================================================================
# Browser HTML Portal & Public Pages Views
# =========================================================================
from django.views.generic import TemplateView
from django.views import View
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.db import transaction

from .forms import LoginForm, RegisterForm, ContactForm
from students.models import StudentProfile
from businesses.models import BusinessProfile

class LandingPageView(TemplateView):
    template_name = 'landing.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Check if user is authenticated and pass profile for templates
        if self.request.user.is_authenticated:
            if self.request.user.role == 'student':
                context['profile'] = StudentProfile.objects.filter(user=self.request.user).first()
            elif self.request.user.role == 'business':
                context['profile'] = BusinessProfile.objects.filter(user=self.request.user).first()
        return context


class LoginPageView(View):
    template_name = 'login.html'

    def get(self, request):
        if request.user.is_authenticated:
            return self._redirect_user(request.user)
        form = LoginForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = LoginForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            auth_login(request, user)
            messages.success(request, f"Welcome back, {user.email}!")
            
            # Handle redirect parameter if present
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return self._redirect_user(user)

        return render(request, self.template_name, {'form': form})

    def _redirect_user(self, user):
        if user.role == 'student':
            return redirect('student_dashboard')
        elif user.role == 'business':
            return redirect('business_dashboard')
        elif user.role == 'admin':
            return redirect('admin_dashboard')
        return redirect('landing')


class RegisterPageView(View):
    template_name = 'register.html'

    def get(self, request):
        if request.user.is_authenticated:
            if request.user.role == 'student':
                return redirect('student_dashboard')
            elif request.user.role == 'business':
                return redirect('business_dashboard')
        # Prepopulate role from GET parameter if provided
        initial_role = request.GET.get('role', 'student')
        form = RegisterForm(initial={'role': initial_role})
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = form.save(commit=False)
                user.set_password(form.cleaned_data['password'])
                user.is_active = True
                user.save()

                role = form.cleaned_data.get('role')
                if role == User.Role.STUDENT:
                    StudentProfile.objects.create(
                        user=user,
                        first_name=form.cleaned_data.get('first_name', ''),
                        last_name=form.cleaned_data.get('last_name', '')
                    )
                elif role == User.Role.BUSINESS:
                    BusinessProfile.objects.create(
                        user=user,
                        company_name=form.cleaned_data.get('company_name', ''),
                        industry='Not Specified',
                        business_registration_no=f"REG-{user.uuid.hex[:8].upper()}"
                    )

                # Log user in immediately on registration
                auth_login(request, user)
                messages.success(request, "Account created successfully!")
                
                if role == User.Role.STUDENT:
                    return redirect('student_dashboard')
                elif role == User.Role.BUSINESS:
                    return redirect('business_dashboard')

        return render(request, self.template_name, {'form': form})


class AboutPageView(TemplateView):
    template_name = 'about.html'


class ContactPageView(View):
    template_name = 'contact.html'

    def get(self, request):
        form = ContactForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = ContactForm(request.POST)
        if form.is_valid():
            # In a real app, send mail or store in database:
            messages.success(request, "Thank you for reaching out! We've received your message and will respond shortly.")
            return redirect('contact_page')
        return render(request, self.template_name, {'form': form})


class LogoutPageView(View):
    def get(self, request):
        auth_logout(request)
        messages.success(request, "You have been logged out.")
        return redirect('landing')

