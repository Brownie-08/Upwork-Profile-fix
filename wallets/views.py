from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from wallets.models import Wallet, Transaction, MomoPayment, LusitoAccount
from wallets.services.momo_service import MTNMoMoService
import json
import logging
import re
import uuid

logger = logging.getLogger(__name__)


def validate_swaziland_phone_number(value):
    """Validate that the phone number is a valid Swaziland number starting with +268."""
    if not value:
        return False, "Phone number is required."
    pattern = r"^\+268[7][0-9]{7}$"
    if not re.match(pattern, value):
        return (
            False,
            "Phone number must start with +268 and be followed by 8 digits (e.g., +26876012345).",
        )
    return True, ""


@login_required
@require_http_methods(["GET", "POST"])
def deposit_funds(request):
    if request.method == "POST":
        amount = request.POST.get("amount")
        phone_number = request.POST.get("phone_number")

        if not amount or not phone_number:
            messages.error(request, "Amount and phone number are required")
            return render(request, "wallets/deposit_funds.html")

        try:
            amount = Decimal(amount)
            if amount <= 0:
                messages.error(request, "Amount must be greater than 0")
                return render(request, "wallets/deposit_funds.html")
        except (ValueError, TypeError):
            messages.error(request, "Invalid amount")
            return render(request, "wallets/deposit_funds.html")

        is_valid, error_message = validate_swaziland_phone_number(phone_number)
        if not is_valid:
            messages.error(request, error_message)
            return render(request, "wallets/deposit_funds.html")

        try:
            wallet = request.user.wallet
        except Wallet.DoesNotExist:
            logger.error(f"Wallet not found for user: {request.user.username}")
            messages.error(request, "User wallet not found")
            return render(request, "wallets/deposit_funds.html")

        external_id = str(uuid.uuid4())
        transaction = Transaction.objects.create(
            wallet=wallet,
            transaction_type="DEPOSIT",
            amount=amount,
            status="PENDING",
            payment_method="MOMO",
            reference_id=external_id,
            description=f"Deposit of E{amount} via MTN MoMo",
            momo_number=phone_number,
        )
        transaction.calculate_fee()

        momo_service = MTNMoMoService()
        result = momo_service.request_to_pay(
            amount=amount,
            phone_number=phone_number,
            external_id=external_id,
            currency=settings.MTN_MOMO_CONFIG["CURRENCY"],
            payer_message=f"Deposit to {request.user.username}'s wallet",
            payee_note=f"Wallet deposit from {phone_number}",
        )

        if result["success"]:
            MomoPayment.objects.create(
                transaction=transaction,
                momo_transaction_id=result["reference_id"],
                phone_number=phone_number,
                payment_status="PROCESSING",
            )
            transaction.status = "PROCESSING"
            transaction.save()
            messages.success(
                request,
                "Payment request sent! Please check your phone to complete the transaction.",
            )
            return redirect(
                "wallets:transaction_status", transaction_id=transaction.reference_id
            )
        else:
            transaction.mark_as_failed(result.get("message", "Unknown error"))
            MomoPayment.objects.create(
                transaction=transaction,
                momo_transaction_id=external_id,
                phone_number=phone_number,
                payment_status="FAILED",
                error_message=result.get("message", "Unknown error"),
            )
            logger.error(
                f"Deposit failed for user {request.user.username}: {result['message']}"
            )
            messages.error(request, "Failed to initiate payment. Please try again.")
            return render(request, "wallets/deposit_funds.html")

    return render(request, "wallets/deposit_funds.html")


@login_required
def wallet_dashboard(request):
    try:
        wallet = Wallet.objects.get(user=request.user)
    except Wallet.DoesNotExist:
        wallet = Wallet.objects.create(user=request.user)
        logger.info(f"Created new wallet for user: {request.user.username}")

    transactions = wallet.transactions.all()[:10]
    summary = Transaction.get_transaction_summary(request.user)

    context = {
        "wallet": wallet,
        "transactions": transactions,
        "summary": summary,
    }
    return render(request, "wallets/wallet_dashboard.html", context)


@csrf_exempt
@require_http_methods(["POST"])
def momo_callback(request):
    try:
        data = json.loads(request.body)
        reference_id = data.get("referenceId")
        status = data.get("status", "").lower()

        if not reference_id or not status:
            logger.error(f"Invalid callback payload: {data}")
            return JsonResponse(
                {"status": "error", "message": "Invalid payload"}, status=400
            )

        try:
            momo_payment = MomoPayment.objects.get(momo_transaction_id=reference_id)
            transaction = momo_payment.transaction

            if status in ["successful", "failed"]:
                momo_payment.payment_status = (
                    "COMPLETED" if status == "successful" else "FAILED"
                )
                momo_payment.error_message = (
                    data.get("reason", "") if status == "failed" else ""
                )
                momo_payment.save()

                if status == "successful":
                    transaction.mark_as_completed()
                    if transaction.transaction_type == "DEPOSIT":
                        transaction.wallet.balance += transaction.amount
                        transaction.wallet.save()
                        lusito_account = LusitoAccount.objects.first()
                        if lusito_account:
                            lusito_account.total_balance += transaction.amount
                            lusito_account.save()
                            logger.info(
                                f"LusitoAccount updated: total_balance={lusito_account.total_balance}"
                            )
                    elif transaction.transaction_type == "WITHDRAWAL":
                        transaction.wallet.balance -= (
                            transaction.amount + transaction.fee_amount
                        )
                        transaction.wallet.save()
                        lusito_account = LusitoAccount.objects.first()
                        if lusito_account:
                            lusito_account.total_balance -= (
                                transaction.amount + transaction.fee_amount
                            )
                            lusito_account.commission_balance += transaction.fee_amount
                            lusito_account.save()
                            logger.info(
                                f"LusitoAccount updated: total_balance={lusito_account.total_balance}, commission_balance={lusito_account.commission_balance}"
                            )
                else:
                    transaction.mark_as_failed(data.get("reason", "Unknown error"))

                transaction.momo_reference = data.get("financialTransactionId", "")
                transaction.save()

                logger.info(f"Transaction {reference_id} updated to status: {status}")
                return JsonResponse({"status": "success"})
            else:
                logger.error(f"Invalid status in callback: {status}")
                return JsonResponse(
                    {"status": "error", "message": "Invalid status"}, status=400
                )

        except MomoPayment.DoesNotExist:
            logger.error(f"Momo payment not found for reference_id: {reference_id}")
            return JsonResponse(
                {"status": "error", "message": "Transaction not found"}, status=404
            )

    except json.JSONDecodeError:
        logger.error("Invalid JSON in callback payload")
        return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"Callback processing failed: {str(e)}")
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@login_required
@require_http_methods(["GET", "POST"])
def withdraw_funds(request):
    if request.method == "POST":
        amount = request.POST.get("amount")
        phone_number = request.POST.get("phone_number")

        if not amount or not phone_number:
            messages.error(request, "Amount and phone number are required")
            return render(request, "wallets/withdraw_funds.html")

        try:
            amount = Decimal(amount)
            if amount <= 0:
                messages.error(request, "Amount must be greater than 0")
                return render(request, "wallets/withdraw_funds.html")
        except (ValueError, TypeError):
            messages.error(request, "Invalid amount")
            return render(request, "wallets/withdraw_funds.html")

        is_valid, error_message = validate_swaziland_phone_number(phone_number)
        if not is_valid:
            messages.error(request, error_message)
            return render(request, "wallets/withdraw_funds.html")

        try:
            wallet = request.user.wallet
            transaction_fee = Decimal("5.00")  # From Transaction.calculate_fee
            if wallet.balance < (amount + transaction_fee):
                messages.error(
                    request, "Insufficient balance (including E5 withdrawal fee)"
                )
                return render(request, "wallets/withdraw_funds.html")
        except Wallet.DoesNotExist:
            logger.error(f"Wallet not found for user: {request.user.username}")
            messages.error(request, "User wallet not found")
            return render(request, "wallets/withdraw_funds.html")

        try:
            lusito_account = LusitoAccount.objects.first()
            if not lusito_account or lusito_account.total_balance < (
                amount + transaction_fee
            ):
                logger.error(
                    f"Insufficient funds in LusitoAccount: total_balance={lusito_account.total_balance if lusito_account else 'None'}"
                )
                messages.error(
                    request, "System funds insufficient. Please contact support."
                )
                return render(request, "wallets/withdraw_funds.html")
        except LusitoAccount.DoesNotExist:
            logger.error("LusitoAccount not found")
            messages.error(
                request, "System account not configured. Please contact support."
            )
            return render(request, "wallets/withdraw_funds.html")

        external_id = str(uuid.uuid4())
        transaction = Transaction.objects.create(
            wallet=wallet,
            transaction_type="WITHDRAWAL",
            amount=amount,
            status="PENDING",
            payment_method="MOMO",
            reference_id=external_id,
            description=f"Withdrawal of E{amount} via MTN MoMo",
            momo_number=phone_number,
        )
        transaction.calculate_fee()

        momo_service = MTNMoMoService()
        result = momo_service.transfer_money(
            amount=amount + transaction.fee_amount,
            phone_number=phone_number,
            external_id=external_id,
            currency=settings.MTN_MOMO_CONFIG["CURRENCY"],
            payee_message=f"Withdrawal from {request.user.username}'s wallet",
            payer_note=f"Wallet withdrawal to {phone_number}",
        )

        if result["success"]:
            MomoPayment.objects.create(
                transaction=transaction,
                momo_transaction_id=result["reference_id"],
                phone_number=phone_number,
                payment_status="PROCESSING",
            )
            transaction.status = "PROCESSING"
            transaction.save()
            messages.success(
                request,
                "Withdrawal request processed! Money will be sent to your phone.",
            )
            return redirect(
                "wallets:transaction_status", transaction_id=transaction.reference_id
            )
        else:
            transaction.mark_as_failed(result.get("message", "Unknown error"))
            MomoPayment.objects.create(
                transaction=transaction,
                momo_transaction_id=external_id,
                phone_number=phone_number,
                payment_status="FAILED",
                error_message=result.get("message", "Unknown error"),
            )
            logger.error(
                f"Withdrawal failed for user {request.user.username}: {result['message']}"
            )
            messages.error(request, "Failed to process withdrawal. Please try again.")
            return render(request, "wallets/withdraw_funds.html")

    return render(request, "wallets/withdraw_funds.html")


@login_required
def transaction_status_view(request, transaction_id):
    try:
        transaction = Transaction.objects.get(
            reference_id=transaction_id, wallet__user=request.user
        )
    except Transaction.DoesNotExist:
        logger.error(
            f"Transaction {transaction_id} not found for user: {request.user.username}"
        )
        messages.error(request, "Transaction not found")
        return redirect("wallets:momo_deposit")

    try:
        momo_payment = transaction.momopayment
    except MomoPayment.DoesNotExist:
        momo_payment = None

    if (
        transaction.status == "PROCESSING"
        and momo_payment
        and momo_payment.payment_status == "PROCESSING"
    ):
        momo_service = MTNMoMoService()
        result = momo_service.get_transaction_status(momo_payment.momo_transaction_id)

        if result["success"]:
            status_data = result["data"]
            momo_status = status_data.get("status", "").lower()

            if momo_status == "successful":
                momo_payment.payment_status = "COMPLETED"
                momo_payment.save()
                transaction.mark_as_completed()

                if transaction.transaction_type == "DEPOSIT":
                    transaction.wallet.balance += transaction.amount
                    transaction.wallet.save()
                    lusito_account = LusitoAccount.objects.first()
                    if lusito_account:
                        lusito_account.total_balance += transaction.amount
                        lusito_account.save()
                        logger.info(
                            f"LusitoAccount updated: total_balance={lusito_account.total_balance}"
                        )
                elif transaction.transaction_type == "WITHDRAWAL":
                    transaction.wallet.balance -= (
                        transaction.amount + transaction.fee_amount
                    )
                    transaction.wallet.save()
                    lusito_account = LusitoAccount.objects.first()
                    if lusito_account:
                        lusito_account.total_balance -= (
                            transaction.amount + transaction.fee_amount
                        )
                        lusito_account.commission_balance += transaction.fee_amount
                        lusito_account.save()
                        logger.info(
                            f"LusitoAccount updated: total_balance={lusito_account.total_balance}, commission_balance={lusito_account.commission_balance}"
                        )

            elif momo_status in ["failed"]:
                momo_payment.payment_status = "FAILED"
                momo_payment.error_message = status_data.get("reason", "Unknown error")
                momo_payment.save()
                transaction.mark_as_failed(status_data.get("reason", "Unknown error"))

            transaction.momo_reference = status_data.get("financialTransactionId", "")
            transaction.save()

    context = {
        "transaction": transaction,
        "momo_payment": momo_payment,
    }
    return render(request, "wallets/transaction_status.html", context)
