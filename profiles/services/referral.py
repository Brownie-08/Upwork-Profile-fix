"""
Referral system service for handling referral codes and user assignments
"""

import logging
import random
import string
from django.contrib.auth.models import User
from django.db import transaction
from ..models import Referral

logger = logging.getLogger(__name__)


class ReferralService:
    """Service class for managing referral operations"""

    CODE_LENGTH = 8  # 8 uppercase characters
    MAX_ATTEMPTS = 10  # Maximum attempts to generate unique code

    @classmethod
    def generate_code(cls):
        """
        Generate a unique uppercase referral code

        Returns:
            str: Unique 8-character uppercase referral code
        """
        attempts = 0
        while attempts < cls.MAX_ATTEMPTS:
            # Generate random 8-character uppercase code
            code = "".join(
                random.choices(
                    string.ascii_uppercase + string.digits, k=cls.CODE_LENGTH
                )
            )

            # Check if code is unique
            if not Referral.objects.filter(code=code).exists():
                logger.info(f"Generated unique referral code: {code}")
                return code

            attempts += 1
            logger.warning(f"Referral code {code} already exists, attempt {attempts}")

        # If all attempts failed, add timestamp to ensure uniqueness
        import time

        timestamp = str(int(time.time()))[-4:]  # Last 4 digits of timestamp
        code = "".join(random.choices(string.ascii_uppercase, k=4)) + timestamp
        logger.warning(
            f"Using timestamp-based code after {cls.MAX_ATTEMPTS} attempts: {code}"
        )
        return code

    @classmethod
    def create_referral(cls, user):
        """
        Create a referral record for a user

        Args:
            user: User instance

        Returns:
            Referral instance or None if failed
        """
        try:
            referral, created = Referral.objects.get_or_create(
                user=user, defaults={"code": cls.generate_code()}
            )

            if created:
                logger.info(
                    f"Created referral for user {user.username} with code {referral.code}"
                )
            else:
                logger.info(
                    f"Referral already exists for user {user.username} with code {referral.code}"
                )

            return referral

        except Exception as e:
            logger.error(f"Error creating referral for user {user.username}: {str(e)}")
            return None

    @classmethod
    def assign_referrer(cls, new_user, referral_code):
        """
        Assign a referrer to a new user based on referral code

        Args:
            new_user: User instance (the new user being referred)
            referral_code: str (the referral code provided)

        Returns:
            tuple (success: bool, message: str, referrer: User or None)
        """
        if not referral_code or not referral_code.strip():
            return True, "No referral code provided", None

        referral_code = referral_code.strip().upper()

        try:
            # Find the referrer by their referral code
            try:
                referrer_referral = Referral.objects.get(code=referral_code)
                referrer = referrer_referral.user
            except Referral.DoesNotExist:
                logger.warning(f"Invalid referral code attempted: {referral_code}")
                return False, f"Invalid referral code: {referral_code}", None

            # Check if user is trying to refer themselves
            if referrer == new_user:
                logger.warning(
                    f"User {new_user.username} attempted to use their own referral code"
                )
                return False, "Cannot use your own referral code", None

            # Create or update the new user's referral record with referrer info
            with transaction.atomic():
                referral, created = Referral.objects.get_or_create(
                    user=new_user,
                    defaults={"code": cls.generate_code(), "referred_by": referrer},
                )

                if not created and not referral.referred_by:
                    # Update existing referral with referrer if not already set
                    referral.referred_by = referrer
                    referral.save()
                elif not created and referral.referred_by:
                    # User already has a referrer
                    logger.warning(
                        f"User {new_user.username} already has referrer {referral.referred_by.username}"
                    )
                    return False, "User already has a referrer", referral.referred_by

            logger.info(
                f"User {new_user.username} referred by {referrer.username} using code {referral_code}"
            )
            return (
                True,
                f"Successfully linked to referrer: {referrer.username}",
                referrer,
            )

        except Exception as e:
            logger.error(
                f"Error assigning referrer for {new_user.username} with code {referral_code}: {str(e)}"
            )
            return False, "An error occurred while processing referral code", None

    @classmethod
    def get_user_referrals(cls, user):
        """
        Get all users referred by a specific user

        Args:
            user: User instance

        Returns:
            QuerySet of User objects
        """
        return User.objects.filter(referral__referred_by=user)

    @classmethod
    def get_referral_stats(cls, user):
        """
        Get referral statistics for a user

        Args:
            user: User instance

        Returns:
            dict: Statistics including total referrals, referral code, etc.
        """
        try:
            referral = Referral.objects.get(user=user)

            stats = {
                "referral_code": referral.code,
                "total_referrals": referral.total_referrals,
                "referred_by": referral.referred_by,
                "created_at": referral.created_at,
                "referred_users": cls.get_user_referrals(user),
            }

            return stats

        except Referral.DoesNotExist:
            # Create referral if it doesn't exist
            referral = cls.create_referral(user)
            if referral:
                return cls.get_referral_stats(user)
            else:
                return {
                    "referral_code": None,
                    "total_referrals": 0,
                    "referred_by": None,
                    "created_at": None,
                    "referred_users": User.objects.none(),
                }

    @classmethod
    def validate_referral_code(cls, code):
        """
        Validate if a referral code exists and is valid

        Args:
            code: str (referral code to validate)

        Returns:
            tuple (is_valid: bool, referrer: User or None)
        """
        if not code or not code.strip():
            return False, None

        code = code.strip().upper()

        try:
            referral = Referral.objects.get(code=code)
            return True, referral.user
        except Referral.DoesNotExist:
            return False, None
