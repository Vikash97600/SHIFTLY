from django.db import models
from django.conf import settings

class BusinessProfile(models.Model):
    class VerificationStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        VERIFIED = 'verified', 'Verified'
        REJECTED = 'rejected', 'Rejected'

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='business_profile')
    company_name = models.CharField(max_length=150)
    company_logo_url = models.URLField(max_length=255, blank=True, null=True)
    website_url = models.URLField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    industry = models.CharField(max_length=100)
    business_registration_no = models.CharField(max_length=50, unique=True)
    tax_id = models.CharField(max_length=50, blank=True, null=True)
    verification_status = models.CharField(
        max_length=20, 
        choices=VerificationStatus.choices, 
        default=VerificationStatus.PENDING
    )
    reputation_score = models.DecimalField(max_digits=5, decimal_places=2, default=100.00)
    latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.company_name


class Earning(models.Model):
    class PaymentStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ESCROW = 'escrow', 'Escrow'
        RELEASED = 'released', 'Released'
        REFUNDED = 'refunded', 'Refunded'
        FAILED = 'failed', 'Failed'

    student = models.ForeignKey('students.StudentProfile', on_delete=models.RESTRICT, related_name='earnings')
    business = models.ForeignKey(BusinessProfile, on_delete=models.RESTRICT, related_name='payments')
    job = models.ForeignKey('jobs.JobPosting', on_delete=models.RESTRICT, related_name='earnings')
    gross_amount = models.DecimalField(max_digits=10, decimal_places=2)
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2)
    net_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(
        max_length=20, 
        choices=PaymentStatus.choices, 
        default=PaymentStatus.PENDING
    )
    payout_method = models.CharField(max_length=50, blank=True, null=True)
    transaction_reference = models.CharField(max_length=100, unique=True, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Tx: {self.transaction_reference} ({self.gross_amount} USD)"
