from django.contrib.auth import get_user_model
from notifications.models import Notification

User = get_user_model()


def create_business_registration_notifications(business_user, business_profile):
    Notification.objects.create(
        user=business_user,
        type=Notification.NotificationType.SYSTEM,
        title="Your business account is pending approval",
        body="Your business account has been received and is currently under review.",
        payload={"status": "pending"},
    )

    admins = User.objects.filter(role=User.Role.ADMIN, is_active=True)
    if not admins.exists():
        return

    title = "New Business Registration Received"
    body = (
        f"{business_profile.company_name} has registered on Shiftly. "
        "Waiting for Admin Approval."
    )
    payload = {
        "business_id": business_user.id,
        "business_name": business_profile.company_name,
        "owner_name": business_user.email,
        "category": business_profile.industry,
    }

    for admin in admins:
        Notification.objects.create(
            user=admin,
            type=Notification.NotificationType.SYSTEM,
            title=title,
            body=body,
            payload=payload,
        )


def create_account_decision_notification(user, approved, reason=""):
    if approved:
        title = "Business Account Approved"
        body = (
            "Your business account has been approved. You can now sign in and access your dashboard."
        )
    else:
        title = "Business Account Rejected"
        body = (
            "Your business account registration was not approved. "
            "Please contact support for more information."
        )
        if reason:
            body = f"{body} Reason: {reason}"

    Notification.objects.create(
        user=user,
        type=Notification.NotificationType.SYSTEM,
        title=title,
        body=body,
        payload={"approved": approved, "reason": reason},
    )
