from rest_framework import serializers
from .models import BusinessProfile

class BusinessProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    uuid = serializers.UUIDField(source='user.uuid', read_only=True)

    class Meta:
        model = BusinessProfile
        fields = (
            'id', 'uuid', 'email', 'company_name', 'company_logo_url', 
            'website_url', 'description', 'industry', 
            'business_registration_no', 'tax_id', 'verification_status', 
            'reputation_score', 'latitude', 'longitude', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'uuid', 'email', 'verification_status', 'reputation_score', 'created_at', 'updated_at')
