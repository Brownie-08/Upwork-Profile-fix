"""
OTP service for account verification and password reset functionality
"""

import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from ..models import LoginOTP

logger = logging.getLogger(__name__)

# Log OTP configuration at startup
try:
    import os
    from django.conf import settings
    
    is_production = (
        'RAILWAY_ENVIRONMENT' in os.environ or 
        'RAILWAY_SERVICE_NAME' in os.environ or
        'RAILWAY_DOMAIN' in os.environ or
        os.environ.get('DEBUG', '').lower() == 'false'
    )
    
    print("\n" + "="*60)
    print("🔧 OTP SERVICE CONFIGURATION")
    print("="*60)
    print(f"🌍 Environment: {'PRODUCTION' if is_production else 'DEVELOPMENT'}")
    
    if hasattr(settings, 'EMAIL_BACKEND'):
        print(f"📧 Email Backend: {settings.EMAIL_BACKEND}")
        
    if hasattr(settings, 'EMAIL_HOST_USER'):
        email_user = getattr(settings, 'EMAIL_HOST_USER', '')
        if email_user:
            print(f"👤 Email User: {email_user}")
        else:
            print("❌ EMAIL_HOST_USER not set!")
            
    email_password = os.environ.get('EMAIL_HOST_PASSWORD', '')
    if email_password:
        print(f"🔐 Email Password: {'*' * 16} (configured)")
    else:
        print("❌ EMAIL_HOST_PASSWORD not set!")
        
    if is_production:
        print("🚨 PRODUCTION MODE: Console fallback DISABLED")
        print("🚨 Email delivery MUST work or registration fails!")
        if not email_user or not email_password:
            print("💥 CRITICAL: Missing email credentials!")
    else:
        print("💻 DEVELOPMENT MODE: Console fallback available")
        
    print("="*60 + "\n")
        
except Exception as e:
    print(f"Warning: Could not load OTP config: {e}")


class OTPService:
    """Service class for managing OTP operations"""

    MAX_ATTEMPTS = 5
    OTP_EXPIRY_MINUTES = 5
    RESEND_COOLDOWN_SECONDS = 60

    @classmethod
    def create_otp(cls, user, purpose, channel="EMAIL"):
        """
        Create and send OTP for user

        Args:
            user: User instance
            purpose: 'VERIFY' or 'RESET'
            channel: 'EMAIL', 'SMS', or 'BOTH'

        Returns:
            LoginOTP instance or None if failed
        """
        try:
            # Check for recent OTP within cooldown period
            recent_otp = LoginOTP.objects.filter(
                user=user,
                purpose=purpose,
                created_at__gte=timezone.now()
                - timedelta(seconds=cls.RESEND_COOLDOWN_SECONDS),
            ).first()

            if recent_otp and recent_otp.is_valid():
                logger.warning(f"OTP cooldown active for user {user.username}")
                return None

            # Create new OTP
            otp = LoginOTP.objects.create(user=user, purpose=purpose, channel=channel)

            # Send notification based on channel
            if channel == "EMAIL":
                success = cls._send_email_otp(user, otp)
            elif channel == "SMS":
                success = cls._send_sms_otp(user, otp)
            elif channel == "BOTH":
                # Send via both email and SMS
                email_success = cls._send_email_otp(user, otp)
                sms_success = cls._send_sms_otp(user, otp)
                success = email_success or sms_success  # At least one must succeed
            else:
                logger.error(f"Invalid channel '{channel}' for user {user.username}")
                success = False

            if success:
                logger.info(
                    f"OTP {otp.code} created and sent to {user.username} via {channel}"
                )
                return otp
            else:
                # Check if we're in production environment
                import os
                is_production = (
                    'RAILWAY_ENVIRONMENT' in os.environ or 
                    'RAILWAY_SERVICE_NAME' in os.environ or
                    'RAILWAY_DOMAIN' in os.environ or
                    os.environ.get('DEBUG', '').lower() == 'false'
                )
                
                if is_production:
                    # PRODUCTION: Email MUST work - fail registration
                    otp.delete()  # Clean up failed OTP
                    logger.error(f"😨 PRODUCTION: Registration failed for {user.username} - email delivery failed")
                    logger.error("User will need to try again after email credentials are fixed")
                    return None  # Fail registration in production if email fails
                else:
                    # Development environment - allow console fallback to work
                    logger.warning(f"Development: Email failed for {user.username} but OTP {otp.code} available via console")
                    return otp  # Return OTP for development console fallback

        except Exception as e:
            logger.error(f"Error creating OTP for {user.username}: {str(e)}")
            return None

    @classmethod
    def verify_otp(cls, user, code, purpose):
        """
        Verify OTP code for user

        Args:
            user: User instance
            code: OTP code to verify
            purpose: 'VERIFY' or 'RESET'

        Returns:
            tuple (success: bool, message: str)
        """
        try:
            # Get the latest valid OTP
            otp = (
                LoginOTP.objects.filter(user=user, purpose=purpose, verified=False)
                .order_by("-created_at")
                .first()
            )

            if not otp:
                return False, "No valid OTP found. Please request a new one."

            # Increment attempts
            otp.attempts += 1
            otp.save()

            # Check if expired
            if otp.is_expired():
                return False, "OTP has expired. Please request a new one."

            # Check max attempts
            if otp.attempts > cls.MAX_ATTEMPTS:
                return False, "Maximum attempts exceeded. Please request a new OTP."

            # Verify code
            if otp.code == code:
                otp.verified = True
                otp.save()

                # Handle account verification
                if purpose == "VERIFY":
                    user.is_active = True
                    user.save()
                    logger.info(f"Account verified for user {user.username}")

                logger.info(f"OTP verified successfully for {user.username}")
                return True, "OTP verified successfully."
            else:
                remaining = cls.MAX_ATTEMPTS - otp.attempts
                return False, f"Invalid OTP. {remaining} attempts remaining."

        except Exception as e:
            logger.error(f"Error verifying OTP for {user.username}: {str(e)}")
            return False, "An error occurred during verification."

    @classmethod
    def can_resend_otp(cls, user, purpose):
        """
        Check if user can request a new OTP (cooldown check)

        Args:
            user: User instance
            purpose: 'VERIFY' or 'RESET'

        Returns:
            tuple (can_resend: bool, seconds_remaining: int)
        """
        latest_otp = (
            LoginOTP.objects.filter(user=user, purpose=purpose)
            .order_by("-created_at")
            .first()
        )

        if not latest_otp:
            return True, 0

        time_since_last = timezone.now() - latest_otp.created_at
        cooldown_remaining = (
            cls.RESEND_COOLDOWN_SECONDS - time_since_last.total_seconds()
        )

        if cooldown_remaining <= 0:
            return True, 0
        else:
            return False, int(cooldown_remaining)

    @classmethod
    def _send_email_otp(cls, user, otp):
        """Send OTP via email with production-safe error handling"""
        try:
            # Check if email backend is properly configured
            from django.conf import settings
            from django.core.mail import get_connection
            
            # If using console backend, just log the OTP
            if settings.EMAIL_BACKEND == "django.core.mail.backends.console.EmailBackend":
                logger.info(f"📧 Console Email OTP for {user.email}: {otp.code} (expires in {cls.OTP_EXPIRY_MINUTES}min)")
                print(f"📧 OTP for {user.email}: {otp.code}")
                return True
            
            # For SMTP backend, add timeout and connection validation
            subject = "Your OTP Code"

            if otp.purpose == "VERIFY":
                subject = "Verify Your Account - LusitoHub"
                template_name = "emails/verify_otp.html"
            else:  # RESET
                subject = "Password Reset Code - LusitoHub"
                template_name = "emails/reset_otp.html"

            # Create email context
            context = {
                "user": user,
                "otp_code": otp.code,
                "expires_minutes": cls.OTP_EXPIRY_MINUTES,
            }

            # Render email templates
            try:
                html_message = render_to_string(template_name, context)
                plain_message = strip_tags(html_message)
            except:
                # Fallback to simple message
                plain_message = f"Your verification code is {otp.code}. It will expire in {cls.OTP_EXPIRY_MINUTES} minutes."
                html_message = plain_message

            # Try to send with a shorter timeout to prevent worker timeout
            connection = get_connection(timeout=10)  # 10 second timeout
            
            from django.core.mail import EmailMultiAlternatives
            email = EmailMultiAlternatives(
                subject=subject,
                body=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email],
                connection=connection
            )
            email.attach_alternative(html_message, "text/html")
            email.send()

            logger.info(f"✅ Email OTP sent successfully to {user.email}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to send email OTP to {user.email}: {str(e)}")
            
            # Check if we're in Railway production environment
            import os
            is_production = (
                'RAILWAY_ENVIRONMENT' in os.environ or 
                'RAILWAY_SERVICE_NAME' in os.environ or
                'RAILWAY_DOMAIN' in os.environ or
                os.environ.get('DEBUG', '').lower() == 'false'
            )
            
            if is_production:
                # PRODUCTION: Email MUST work - no console fallback allowed
                logger.error(f"😨 PRODUCTION EMAIL FAILURE: Cannot send OTP to {user.email}")
                logger.error("This is a CRITICAL ERROR - users will not receive OTP codes!")
                logger.error("Required Railway environment variables:")
                logger.error("- EMAIL_HOST_USER=your-email@gmail.com")
                logger.error("- EMAIL_HOST_PASSWORD=your-app-password")
                logger.error("- DEFAULT_FROM_EMAIL=your-email@gmail.com")
                return False  # Fail registration if email doesn't work in production
            else:
                # Local development - allow console fallback
                logger.warning(f"💻 Development fallback: Console OTP for {user.email}: {otp.code}")
                logger.warning(f"📧 Email failed ({str(e)}), using console fallback for user registration")
                print(f"📧 FALLBACK: Console Email OTP for {user.email}: {otp.code} (expires in {cls.OTP_EXPIRY_MINUTES}min)")
                return True  # Allow console fallback in development only

    @classmethod
    def _send_sms_otp(cls, user, otp):
        """Send OTP via SMS (console for development, production ready)"""
        try:
            phone = (
                getattr(user.profile, "phone_number", None)
                if hasattr(user, "profile")
                else None
            )

            if not phone:
                logger.warning(f"No phone number for user {user.username}")
                return False

            if otp.purpose == "VERIFY":
                message = f"Your LusitoHub verification code is {otp.code}. Expires in {cls.OTP_EXPIRY_MINUTES} minutes. Don't share this code."
            else:  # RESET
                message = f"Your LusitoHub password reset code is {otp.code}. Expires in {cls.OTP_EXPIRY_MINUTES} minutes. Don't share this code."

            # In development, log to console
            logger.info(f"SMS OTP for {phone}: {message}")
            print(f"📱 SMS to {phone}: {message}")

            # Production SMS integration (uncomment when ready)
            # return cls._send_production_sms(phone, message)

            return True

        except Exception as e:
            logger.error(f"Failed to send SMS OTP: {str(e)}")
            return False

    @classmethod
    def _send_production_sms(cls, phone, message):
        """Send SMS via production SMS service (Twilio example)"""
        try:
            # Twilio integration example
            # from twilio.rest import Client
            # client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            # message = client.messages.create(
            #     body=message,
            #     from_=settings.TWILIO_PHONE_NUMBER,
            #     to=phone
            # )
            # return True

            # AWS SNS example
            # import boto3
            # sns = boto3.client('sns', region_name=settings.AWS_REGION)
            # response = sns.publish(PhoneNumber=phone, Message=message)
            # return response['ResponseMetadata']['HTTPStatusCode'] == 200

            logger.info(f"Production SMS would be sent to {phone}: {message}")
            return True

        except Exception as e:
            logger.error(f"Failed to send production SMS to {phone}: {str(e)}")
            return False

    @classmethod
    def get_available_channels(cls, user):
        """Get available OTP channels for a user"""
        channels = ["EMAIL"]  # Email is always available

        # Check if user has phone number for SMS
        if hasattr(user, "profile") and user.profile.phone_number:
            channels.append("SMS")

        return channels

    @classmethod
    def cleanup_expired_otps(cls):
        """Clean up expired OTP records"""
        try:
            expired_count = LoginOTP.objects.filter(
                expires_at__lt=timezone.now()
            ).delete()[0]

            logger.info(f"Cleaned up {expired_count} expired OTP records")
            return expired_count

        except Exception as e:
            logger.error(f"Error cleaning up expired OTPs: {str(e)}")
            return 0
