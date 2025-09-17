from django.core.management.base import BaseCommand
from wallets.services.momo_service import MTNMoMoService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Set up MTN MoMo API user and key for the application"

    def handle(self, *args, **options):
        momo_service = MTNMoMoService()
        result = momo_service.setup_api_user()

        if result["success"]:
            api_user_id = result["api_user_id"]
            api_key = result["api_key"]
            self.stdout.write(
                self.style.SUCCESS(
                    f"API User created successfully!\n"
                    f"API User ID: {api_user_id}\n"
                    f"API Key: {api_key}\n"
                    f"Add these to your .env file:\n"
                    f"MOMO_API_USER_ID={api_user_id}\n"
                    f"MOMO_API_KEY={api_key}"
                )
            )
        else:
            logger.error(f"API user setup failed: {result['message']}")
            self.stdout.write(
                self.style.ERROR(f"Failed to set up API user: {result['message']}")
            )
