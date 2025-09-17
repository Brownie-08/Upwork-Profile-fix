from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
import uuid
import re


def validate_swaziland_phone_number(value):
    """Validate that the phone number is a valid Swaziland number starting with +268."""
    if not value:
        raise models.ValidationError("Phone number is required.")
    # Ensure phone number starts with +268 and has 8 digits after (total length 12)
    pattern = r"^\+268[7][0-9]{7}$"
    if not re.match(pattern, value):
        raise models.ValidationError(
            "Phone number must start with +268 and be followed by 8 digits (e.g., +26876012345)."
        )


class MomoPayment(models.Model):
    PAYMENT_STATUS = [
        ("PENDING", "Pending"),
        ("PROCESSING", "Processing"),
        ("COMPLETED", "Completed"),
        ("FAILED", "Failed"),
    ]

    transaction = models.OneToOneField(
        "Transaction", on_delete=models.CASCADE, related_name="momopayment"
    )
    momo_transaction_id = models.CharField(max_length=100, unique=True)
    phone_number = models.CharField(
        max_length=12, validators=[validate_swaziland_phone_number]
    )
    payment_status = models.CharField(
        max_length=20, choices=PAYMENT_STATUS, default="PENDING"
    )
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"MOMO Payment {self.momo_transaction_id}"


class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Wallet (E {self.balance})"


class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ("DEPOSIT", "Deposit"),
        ("WITHDRAWAL", "Withdrawal"),
        ("PAYMENT", "Project Payment"),
        ("REFUND", "Project Refund"),
    ]

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("PROCESSING", "Processing"),
        ("COMPLETED", "Completed"),
        ("FAILED", "Failed"),
        ("CANCELLED", "Cancelled"),
    ]

    wallet = models.ForeignKey(
        "Wallet", on_delete=models.CASCADE, related_name="transactions"
    )
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    payment_method = models.CharField(
        max_length=20,
        choices=[("MOMO", "MTN Mobile Money"), ("eMALI", "e-Mali")],
        default="MOMO",
        null=True,
    )
    reference_id = models.CharField(max_length=100, unique=True, default=uuid.uuid4)
    description = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    fee_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    fee_description = models.CharField(max_length=255, blank=True)
    momo_number = models.CharField(max_length=15, blank=True, null=True)
    momo_network = models.CharField(max_length=20, blank=True, null=True)
    momo_reference = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["reference_id"]),
            models.Index(fields=["wallet", "status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.transaction_type} - {self.amount} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.reference_id:
            self.reference_id = str(uuid.uuid4())
        super().save(*args, **kwargs)

    @property
    def total_amount(self):
        return self.amount + self.fee_amount

    def mark_as_completed(self):
        self.status = "COMPLETED"
        self.completed_at = timezone.now()
        self.save()

    def mark_as_failed(self, error_message=None):
        self.status = "FAILED"
        if error_message:
            self.notes = f"{self.notes}\nError: {error_message}".strip()
        self.save()

    def calculate_fee(self):
        if self.transaction_type == "WITHDRAWAL":
            self.fee_amount = Decimal("5.00")
            self.fee_description = "E5 withdrawal fee"
        elif self.transaction_type == "DEPOSIT":
            self.fee_amount = Decimal("0.00")
            self.fee_description = "No fee"
        self.save()

    @classmethod
    def get_user_transactions(cls, user, status=None, transaction_type=None):
        transactions = cls.objects.filter(wallet__user=user)
        if status:
            transactions = transactions.filter(status=status)
        if transaction_type:
            transactions = transactions.filter(transaction_type=transaction_type)
        return transactions

    @classmethod
    def get_transaction_summary(cls, user, start_date=None, end_date=None):
        transactions = cls.get_user_transactions(user)
        if start_date:
            transactions = transactions.filter(created_at__gte=start_date)
        if end_date:
            transactions = transactions.filter(created_at__lte=end_date)

        deposits = transactions.filter(
            transaction_type="DEPOSIT", status="COMPLETED"
        ).aggregate(total=models.Sum("amount"))["total"] or Decimal("0.00")
        withdrawals = transactions.filter(
            transaction_type="WITHDRAWAL", status="COMPLETED"
        ).aggregate(total=models.Sum("amount"))["total"] or Decimal("0.00")
        fees = transactions.filter(status="COMPLETED").aggregate(
            total=models.Sum("fee_amount")
        )["total"] or Decimal("0.00")

        return {
            "total_deposits": deposits,
            "total_withdrawals": withdrawals,
            "total_fees": fees,
            "net_movement": deposits - withdrawals - fees,
        }


class LusitoAccount(models.Model):
    total_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    held_funds = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    commission_balance = models.DecimalField(
        max_digits=12, decimal_places=2, default=0.00
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Lusito Account (Balance: E {self.total_balance})"

    def hold_project_funds(self, amount):
        self.held_funds += amount
        self.total_balance += amount
        self.save()

    def release_project_funds(self, amount, commission_rate):
        if self.held_funds >= amount:
            commission_amount = amount * Decimal(str(commission_rate))
            freelancer_payment = amount - commission_amount
            self.held_funds -= amount
            self.total_balance -= freelancer_payment
            self.commission_balance += commission_amount
            self.save()
            return freelancer_payment, commission_amount
        return None, None


class ProjectFund(models.Model):
    STATUS_CHOICES = [
        ("HELD", "Funds Held"),
        ("RELEASED", "Funds Released"),
        ("REFUNDED", "Funds Refunded"),
    ]

    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="HELD")
    held_at = models.DateTimeField(auto_now_add=True)
    released_at = models.DateTimeField(null=True, blank=True)
    commission_rate = models.DecimalField(max_digits=4, decimal_places=2, default=0.10)
    commission_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    reference_id = models.CharField(max_length=100, unique=True, default=uuid.uuid4)

    def __str__(self):
        return f"Project Fund: {self.project.title} - E {self.amount}"

    def release_funds(self):
        if self.status == "HELD":
            self.commission_amount = self.amount * self.commission_rate
            self.status = "RELEASED"
            self.released_at = timezone.now()
            self.save()
            return self.commission_amount
        return None


class CommissionTransaction(models.Model):
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    rate = models.DecimalField(max_digits=4, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    reference_id = models.CharField(max_length=100, unique=True, default=uuid.uuid4)
    description = models.CharField(max_length=255)

    def __str__(self):
        return f"Commission: {self.project.title} - E {self.amount}"
