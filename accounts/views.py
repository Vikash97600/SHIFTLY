from rest_framework import status, generics, permissions
from rest_framework.exceptions import AuthenticationFailed
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

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as exc:
            raise AuthenticationFailed("Invalid email or password") from exc
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


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
from django.contrib.auth import get_user_model

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
        initial_role = request.GET.get('role', 'student')
        if initial_role not in {User.Role.STUDENT, User.Role.BUSINESS}:
            initial_role = User.Role.STUDENT
        form = RegisterForm(initial={'role': initial_role})
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = RegisterForm(request.POST, request.FILES)
        if form.is_valid():
            with transaction.atomic():
                role = form.cleaned_data.get('role')
                if role == User.Role.ADMIN:
                    form.add_error('role', 'Admin registration is not allowed publicly.')
                    return render(request, self.template_name, {'form': form})

                user = form.save(commit=False)
                user.set_password(form.cleaned_data['password'])
                user.is_active = role != User.Role.BUSINESS
                user.status = User.AccountStatus.PENDING if role == User.Role.BUSINESS else User.AccountStatus.APPROVED
                user.is_verified = role != User.Role.BUSINESS
                user.save()

                if role == User.Role.STUDENT:
                    StudentProfile.objects.create(
                        user=user,
                        first_name=form.cleaned_data.get('first_name', ''),
                        last_name=form.cleaned_data.get('last_name', '')
                    )
                elif role == User.Role.BUSINESS:
                    from django.utils import timezone
                    from accounts.models import Verification

                    business_profile = BusinessProfile.objects.create(
                        user=user,
                        company_name=form.cleaned_data.get('company_name', ''),
                        owner_name=form.cleaned_data.get('owner_name', ''),
                        mobile_number=form.cleaned_data.get('mobile_number', ''),
                        address=form.cleaned_data.get('address', ''),
                        business_category=form.cleaned_data.get('business_category', ''),
                        gst_number=form.cleaned_data.get('gst_number', ''),
                        business_license=form.cleaned_data.get('business_license'),
                        gst_document=form.cleaned_data.get('gst_document'),
                        tax_document=form.cleaned_data.get('tax_document'),
                        status='PENDING',
                        is_verified=False,
                        is_active=False,
                        verification_requested_at=timezone.now(),
                        industry=form.cleaned_data.get('business_category', 'Not Specified'),
                        business_registration_no=form.cleaned_data.get('gst_number') or f"REG-{user.uuid.hex[:8].upper()}"
                    )
                    from .utils import create_business_registration_notifications
                    create_business_registration_notifications(user, business_profile)

                    # Create Verification models for uploads
                    if business_profile.business_license:
                        Verification.objects.create(
                            user=user,
                            document_type=Verification.DocumentType.BUSINESS_LICENSE,
                            document_url=business_profile.business_license.url,
                            status=Verification.Status.PENDING
                        )
                    if business_profile.gst_document:
                        Verification.objects.create(
                            user=user,
                            document_type=Verification.DocumentType.TAX_DOCUMENT,
                            document_url=business_profile.gst_document.url,
                            status=Verification.Status.PENDING
                        )
                    if business_profile.tax_document:
                        Verification.objects.create(
                            user=user,
                            document_type=Verification.DocumentType.TAX_DOCUMENT,
                            document_url=business_profile.tax_document.url,
                            status=Verification.Status.PENDING
                        )

                if role == User.Role.STUDENT:
                    auth_login(request, user)
                    messages.success(request, "Account created successfully!")
                    return redirect('student_dashboard')
                elif role == User.Role.BUSINESS:
                    messages.success(request, "Your business account has been submitted for approval.")
                    return redirect('login_page')

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
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']

            user = None
            if request.user.is_authenticated and request.user.email == email:
                user = request.user
            else:
                try:
                    user = User.objects.get(email=email)
                except User.DoesNotExist:
                    pass

            from accounts.models import UserQuery
            UserQuery.objects.create(
                user=user,
                name=name,
                email=email,
                subject=subject,
                message=message
            )

            messages.success(request, "Thank you for reaching out! We've received your message and will respond shortly.")
            return redirect('contact_page')
        return render(request, self.template_name, {'form': form})


class LogoutPageView(View):
    def get(self, request):
        auth_logout(request)
        messages.success(request, "You have been logged out.")
        return redirect('landing')


from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from accounts.models import UserQuery, QueryMessage

class UserQueriesView(LoginRequiredMixin, View):
    template_name = 'accounts/user_queries.html'

    def get(self, request):
        profile = None
        base_template = 'students/base.html'
        if request.user.role == 'student':
            from students.models import StudentProfile
            profile = StudentProfile.objects.filter(user=request.user).first()
            base_template = 'students/base.html'
        elif request.user.role == 'business':
            from businesses.models import BusinessProfile
            profile = BusinessProfile.objects.filter(user=request.user).first()
            base_template = 'businesses/base.html'

        queries = UserQuery.objects.filter(Q(user=request.user) | Q(email=request.user.email)).order_by('-created_at')

        context = {
            'profile': profile,
            'base_template': base_template,
            'queries': queries,
        }
        return render(request, self.template_name, context)


class UserQueryChatView(LoginRequiredMixin, View):
    template_name = 'accounts/user_query_chat.html'

    def get_query(self, request, query_id):
        return get_object_or_404(UserQuery, Q(user=request.user) | Q(email=request.user.email), id=query_id)

    def get(self, request, query_id):
        query = self.get_query(request, query_id)
        
        profile = None
        base_template = 'students/base.html'
        if request.user.role == 'student':
            from students.models import StudentProfile
            profile = StudentProfile.objects.filter(user=request.user).first()
            base_template = 'students/base.html'
        elif request.user.role == 'business':
            from businesses.models import BusinessProfile
            profile = BusinessProfile.objects.filter(user=request.user).first()
            base_template = 'businesses/base.html'

        messages_list = query.chat_messages.all().order_by('created_at')

        context = {
            'profile': profile,
            'base_template': base_template,
            'query': query,
            'chat_messages': messages_list,
        }
        return render(request, self.template_name, context)

    def post(self, request, query_id):
        query = self.get_query(request, query_id)
        message_text = request.POST.get('message', '').strip()
        if message_text:
            QueryMessage.objects.create(
                query=query,
                sender=request.user,
                message=message_text
            )
            if not query.user:
                query.user = request.user
                query.save(update_fields=['user'])
                
        return redirect('user_query_chat', query_id=query.id)


