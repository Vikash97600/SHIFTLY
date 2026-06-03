from rest_framework import serializers
from .models import StudentProfile, StudentSkill, Skill

class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ('id', 'name', 'category')


class StudentSkillSerializer(serializers.ModelSerializer):
    skill = SkillSerializer(read_only=True)
    skill_id = serializers.PrimaryKeyRelatedField(
        queryset=Skill.objects.all(), write_only=True, source='skill'
    )

    class Meta:
        model = StudentSkill
        fields = ('skill', 'skill_id', 'level', 'is_verified')
        read_only_fields = ('is_verified',)


class StudentProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    uuid = serializers.UUIDField(source='user.uuid', read_only=True)
    skills = StudentSkillSerializer(many=True, read_only=True)

    class Meta:
        model = StudentProfile
        fields = (
            'id', 'uuid', 'email', 'first_name', 'last_name', 'bio', 
            'resume_url', 'profile_picture_url', 'reputation_score', 
            'hourly_rate_expectation', 'availability_status', 
            'latitude', 'longitude', 'skills', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'uuid', 'email', 'reputation_score', 'created_at', 'updated_at')
