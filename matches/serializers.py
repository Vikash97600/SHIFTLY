from rest_framework import serializers
from .models import Match

class MatchSerializer(serializers.ModelSerializer):
    job_title = serializers.CharField(source='job.title', read_only=True)
    company_name = serializers.CharField(source='job.business.company_name', read_only=True)
    student_first_name = serializers.CharField(source='student.first_name', read_only=True)
    student_last_name = serializers.CharField(source='student.last_name', read_only=True)
    base_pay = serializers.DecimalField(source='job.base_pay', max_digits=10, decimal_places=2, read_only=True)
    location_name = serializers.CharField(source='job.location_name', read_only=True)

    class Meta:
        model = Match
        fields = (
            'id', 'uuid', 'student', 'student_first_name', 'student_last_name',
            'job', 'job_title', 'company_name', 'base_pay', 'location_name',
            'status', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'uuid', 'created_at', 'updated_at')
