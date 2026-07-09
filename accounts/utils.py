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

    title = "🔔 New Business Registration"
    body = (
        f"{business_profile.company_name} has requested verification.\n"
        "Waiting for approval."
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
        title = "🎉 Congratulations!"
        body = (
            "Your business has been verified.\n"
            "You can now login and post jobs."
        )
    else:
        title = "Verification Request Rejected"
        body = (
            "Your verification request has been rejected.\n"
            f"Reason:\n{reason if reason else 'Incomplete documents.'}"
        )

    Notification.objects.create(
        user=user,
        type=Notification.NotificationType.SYSTEM,
        title=title,
        body=body,
        payload={"approved": approved, "reason": reason},
    )
