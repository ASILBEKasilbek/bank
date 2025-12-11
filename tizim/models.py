from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models.signals import post_save


User = get_user_model()


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    profile_image = models.ImageField(upload_to="profiles/", blank=True, null=True)
    face_reference = models.ImageField(upload_to="faces/", blank=True, null=True)
    is_face_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} profile"


class Transaction(models.Model):
    class TransactionType(models.TextChoices):
        TRANSFER_OUT = ("transfer_out", "Pul o'tkazish (chiqish)")
        TRANSFER_IN = ("transfer_in", "Pul o'tkazish (kirish)")
        TOP_UP = ("top_up", "Kartani to'ldirish")
        ADMIN_ADJUSTMENT = ("admin_adjustment", "Admin o'zgartirish")
        FAKE_PAYMENT = ("fake_payment", "Fake to'lov")

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="transactions")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_type = models.CharField(max_length=32, choices=TransactionType.choices)
    description = models.CharField(max_length=255, blank=True)
    counterparty = models.CharField(max_length=255, blank=True)
    performed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="performed_transactions",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} - {self.transaction_type} - {self.amount}"


def _create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


post_save.connect(_create_user_profile, sender=settings.AUTH_USER_MODEL)
