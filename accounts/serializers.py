from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from django.db import transaction
from django.utils import timezone
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from students.models import StudentProfile
from businesses.models import BusinessProfile
from accounts.models import Verification
from .utils import create_business_registration_notifications

User = get_user_model()

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        try:
            user = User.objects.get(email=email)
            if user.check_password(password):
                if user.role == User.Role.BUSINESS:
                    profile = getattr(user, 'business_profile', None)
                    if not profile or profile.status != 'APPROVED' or user.status != User.AccountStatus.APPROVED:
                        raise serializers.ValidationError({"detail": "Your business account is currently under review."})
                if not user.is_active:
                    raise serializers.ValidationError({"detail": "This account is currently inactive."})
                user = authenticate(username=email, password=password)
            else:
                user = None
        except User.DoesNotExist:
            user = None

        if user is None:
            raise serializers.ValidationError({"detail": "No active account found with the given credentials"})

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
    owner_name = serializers.CharField(required=False, write_only=True, allow_blank=True)
    mobile_number = serializers.CharField(required=False, write_only=True, allow_blank=True)
    address = serializers.CharField(required=False, write_only=True, allow_blank=True)
    business_category = serializers.CharField(required=False, write_only=True, allow_blank=True)
    gst_number = serializers.CharField(required=False, write_only=True, allow_blank=True)
    business_license = serializers.FileField(required=False, write_only=True, allow_null=True)
    gst_document = serializers.FileField(required=False, write_only=True, allow_null=True)
    tax_document = serializers.FileField(required=False, write_only=True, allow_null=True)

    class Meta:
        model = User
        fields = ('email', 'password', 'role', 'first_name', 'last_name', 'company_name',
                  'owner_name', 'mobile_number', 'address', 'business_category',
                  'gst_number', 'business_license', 'gst_document', 'tax_document')

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
            if not attrs.get('owner_name'):
                raise serializers.ValidationError({"owner_name": "Required for business registration"})
            if not attrs.get('mobile_number'):
                raise serializers.ValidationError({"mobile_number": "Required for business registration"})
            if not attrs.get('address'):
                raise serializers.ValidationError({"address": "Required for business registration"})
            if not attrs.get('business_category'):
                raise serializers.ValidationError({"business_category": "Required for business registration"})
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
                owner_name=validated_data.get('owner_name', ''),
                mobile_number=validated_data.get('mobile_number', ''),
                address=validated_data.get('address', ''),
                business_category=validated_data.get('business_category', ''),
                gst_number=validated_data.get('gst_number', ''),
                business_license=validated_data.get('business_license'),
                gst_document=validated_data.get('gst_document'),
                tax_document=validated_data.get('tax_document'),
                status='PENDING',
                is_verified=False,
                is_active=False,
                verification_requested_at=timezone.now(),
                industry=validated_data.get('business_category', 'Not Specified'),
                business_registration_no=validated_data.get('gst_number') or f"REG-{user.uuid.hex[:8].upper()}"
            )
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
