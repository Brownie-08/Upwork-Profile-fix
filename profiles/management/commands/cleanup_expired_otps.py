from django.core.management.base import BaseCommand
from profiles.services.otp import OTPService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Delete expired OTP records"

    def handle(self, *args, **options):
        try:
            deleted = OTPService.cleanup_expired_otps()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully deleted {deleted} expired OTP records"
                )
            )
            logger.info(f"Cleaned up {deleted} expired OTP records")
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error cleaning up expired OTPs: {str(e)}")
            )
            logger.error(f"Error in cleanup_expired_otps command: {str(e)}")
