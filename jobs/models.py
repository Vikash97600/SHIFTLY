import uuid
from django.db import models
from businesses.models import BusinessProfile
from students.models import Skill

class JobPosting(models.Model):
    class WorkType(models.TextChoices):
        REMOTE = 'remote', 'Remote'
        HYBRID = 'hybrid', 'Hybrid'
        ONSITE = 'onsite', 'Onsite'

    class RateType(models.TextChoices):
        HOURLY = 'hourly', 'Hourly'
        FIXED = 'fixed', 'Fixed'

    class JobStatus(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        ACTIVE = 'active', 'Active'
        FILLED = 'filled', 'Filled'
        ARCHIVED = 'archived', 'Archived'
        CANCELLED = 'cancelled', 'Cancelled'

    class JobCategory(models.TextChoices):
        CAFE_RESTAURANT = 'cafe_restaurant', '☕ Cafe / Restaurant'
        RETAIL_SHOP = 'retail_shop', '🛍 Retail Shop'
        OFFICE_ASSISTANT = 'office_assistant', '🏢 Office Assistant'
        EVENT_STAFFING = 'event_staffing', '🎪 Event Staffing'
        DELIVERY_PARTNER = 'delivery_partner', '🚚 Delivery Partner'
        VIDEO_EDITOR = 'video_editor', '🎥 Video Editor'
        GRAPHIC_DESIGNER = 'graphic_designer', '🎨 Graphic Designer'
        SOFTWARE_DEVELOPER = 'software_developer', '💻 Software Developer'

    class JobMode(models.TextChoices):
        ONSITE = 'onsite', 'On-site'
        REMOTE = 'remote', 'Remote'

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    business = models.ForeignKey(BusinessProfile, on_delete=models.RESTRICT, related_name='jobs')
    title = models.CharField(max_length=255)
    description = models.TextField()
    work_type = models.CharField(max_length=20, choices=WorkType.choices, default=WorkType.ONSITE)
    location_name = models.CharField(max_length=255)
    latitude = models.DecimalField(max_digits=10, decimal_places=8)
    longitude = models.DecimalField(max_digits=11, decimal_places=8)
    base_pay = models.DecimalField(max_digits=10, decimal_places=2)
    rate_type = models.CharField(max_length=20, choices=RateType.choices, default=RateType.HOURLY)
    start_date = models.DateField()
    end_date = models.DateField()
    shift_start_time = models.TimeField()
    shift_end_time = models.TimeField()
    slots_available = models.PositiveIntegerField(default=1)
    slots_filled = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=JobStatus.choices, default=JobStatus.DRAFT)
    
    # Dynamic Hiring Radius System Fields
    category = models.CharField(max_length=50, choices=JobCategory.choices, default=JobCategory.CAFE_RESTAURANT)
    job_mode = models.CharField(max_length=20, choices=JobMode.choices, default=JobMode.ONSITE)
    hiring_radius = models.DecimalField(max_digits=5, decimal_places=2, default=4.00, null=True, blank=True)
    is_urgent = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} at {self.business.company_name}"

    @property
    def hired_matches(self):
        return self.matches.filter(status='hired').select_related('student')

    @property
    def applied_candidates_count(self):
        return self.applications.filter(status='applied').count()


class JobRequiredSkill(models.Model):
    class Priority(models.TextChoices):
        REQUIRED = 'required', 'Required'
        PREFERRED = 'preferred', 'Preferred'

    job = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name='required_skills')
    skill = models.ForeignKey(Skill, on_delete=models.RESTRICT, related_name='jobs_requiring')
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.REQUIRED)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('job', 'skill')

    def __str__(self):
        return f"{self.job.title} requires {self.skill.name} ({self.priority})"


class HaversineDistance(models.Func):
    output_field = models.FloatField()

    def __init__(self, lat1, lon1, lat2, lon2):
        super().__init__(lat1, lon1, lat2, lon2)

    def as_sqlite(self, compiler, connection, **extra_context):
        return super().as_sql(compiler, connection, function='haversine', **extra_context)

    def as_mysql(self, compiler, connection, **extra_context):
        sql = "ST_Distance_Sphere(POINT(%s, %s), POINT(%s, %s)) / 1000.0"
        compiled_args = []
        params = []
        for arg in self.source_expressions:
            arg_sql, arg_params = compiler.compile(arg)
            compiled_args.append(arg_sql)
            params.extend(arg_params)
        formatted_sql = sql % (compiled_args[1], compiled_args[0], compiled_args[3], compiled_args[2])
        return formatted_sql, params

    def as_sql(self, compiler, connection, **extra_context):
        sql = (
            "6371.0 * ACOS("
            "SIN(RADIANS(%s)) * SIN(RADIANS(%s)) + "
            "COS(RADIANS(%s)) * COS(RADIANS(%s)) * COS(RADIANS(%s) - RADIANS(%s))"
            ")"
        )
        compiled_args = []
        params = []
        for arg in self.source_expressions:
            arg_sql, arg_params = compiler.compile(arg)
            compiled_args.append(arg_sql)
            params.extend(arg_params)
        formatted_sql = sql % (
            compiled_args[0], compiled_args[2],
            compiled_args[0], compiled_args[2],
            compiled_args[3], compiled_args[1]
        )
        return formatted_sql, params

