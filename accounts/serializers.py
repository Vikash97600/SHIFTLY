from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from django.db import transaction
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from students.models import StudentProfile
from businesses.models import BusinessProfile
from .utils import create_business_registration_notifications

User = get_user_model()

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        user = authenticate(username=email, password=password)

        if user is None:
            raise serializers.ValidationError({"detail": "No active account found with the given credentials"})
        if user.role == User.Role.BUSINESS and user.status != User.AccountStatus.APPROVED:
            raise serializers.ValidationError({"detail": "Your business account is currently under review."})

        self.user = user
        data = super().validate(attrs)
        data['role'] = self.user.role
        data['email'] = self.user.email
        data['uuid'] = str(self.user.uuid)
        return data

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'uuid', 'email', 'role', 'is_active', 'mfa_secret', 'created_at')
        read_only_fields = ('id', 'uuid', 'is_active', 'created_at')


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(required=False, write_only=True, allow_blank=True)
    last_name = serializers.CharField(required=False, write_only=True, allow_blank=True)
    company_name = serializers.CharField(required=False, write_only=True, allow_blank=True)

    class Meta:
        model = User
        fields = ('email', 'password', 'role', 'first_name', 'last_name', 'company_name')

    def validate(self, attrs):
        role = attrs.get('role')
        if role == User.Role.ADMIN:
            raise serializers.ValidationError({"role": "Admin registration is not allowed publicly."})
        if role == User.Role.STUDENT:
            if not attrs.get('first_name') or not attrs.get('last_name'):
                raise serializers.ValidationError({"first_name": "Required for student registration"})
        elif role == User.Role.BUSINESS:
            if not attrs.get('company_name'):
                raise serializers.ValidationError({"company_name": "Required for business registration"})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        email = validated_data['email']
        password = validated_data['password']
        role = validated_data['role']

        user = User.objects.create_user(
            email=email,
            password=password,
            role=role,
            is_active=role != User.Role.BUSINESS,
            status=User.AccountStatus.PENDING if role == User.Role.BUSINESS else User.AccountStatus.APPROVED,
            is_verified=role != User.Role.BUSINESS,
        )

        # Scaffolding profile records based on registered role
        if role == User.Role.STUDENT:
            StudentProfile.objects.create(
                user=user,
                first_name=validated_data.get('first_name', ''),
                last_name=validated_data.get('last_name', '')
            )
        elif role == User.Role.BUSINESS:
            business_profile = BusinessProfile.objects.create(
                user=user,
                company_name=validated_data.get('company_name', ''),
                industry='Not Specified',
                business_registration_no=f"REG-{user.uuid.hex[:8].upper()}"
            )
            create_business_registration_notifications(user, business_profile)

        return user


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("No user is registered with this email.")
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    password = serializers.CharField(min_length=8, write_only=True)
    token = serializers.CharField()
    uidb64 = serializers.CharField()
