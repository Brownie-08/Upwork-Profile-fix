"""
Custom email backends for Railway deployment
"""

import json
import logging
from django.core.mail.backends.base import BaseEmailBackend
from django.conf import settings
import requests

logger = logging.getLogger(__name__)


class ResendEmailBackend(BaseEmailBackend):
    """
    Email backend using Resend API - Railway friendly
    
    Resend is designed for developers and works well with cloud platforms.
    Free tier: 3,000 emails/month, which is perfect for OTP verification.
    
    Setup:
    1. Create account at https://resend.com
    2. Get API key from dashboard
    3. Set RESEND_API_KEY in Railway environment variables
    """

    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently, **kwargs)
        self.api_key = getattr(settings, 'RESEND_API_KEY', '')
        self.api_url = 'https://api.resend.com/emails'

    def send_messages(self, email_messages):
        """
        Send email messages using Resend API
        
        Returns the number of successfully sent messages.
        """
        if not self.api_key:
            logger.error("RESEND_API_KEY not configured")
            if not self.fail_silently:
                raise ValueError("RESEND_API_KEY not configured")
            return 0

        sent_count = 0
        
        for message in email_messages:
            try:
                # Prepare email data for Resend API
                # Use Resend's sandbox domain for unverified domains
                from_email = message.from_email or settings.DEFAULT_FROM_EMAIL
                
                # If using Gmail domain, switch to Resend sandbox domain
                if '@gmail.com' in from_email.lower() or '@lusitohub.com' in from_email.lower():
                    from_email = 'onboarding@resend.dev'  # Resend's verified domain
                
                email_data = {
                    'from': from_email,
                    'to': message.to,
                    'subject': message.subject,
                    'html': message.body if message.content_subtype == 'html' else None,
                    'text': message.body if message.content_subtype == 'plain' else None,
                }
                
                # If we have both HTML and plain text alternatives
                if hasattr(message, 'alternatives') and message.alternatives:
                    for alternative in message.alternatives:
                        if alternative[1] == 'text/html':
                            email_data['html'] = alternative[0]
                
                # Add plain text version if we only have HTML
                if email_data.get('html') and not email_data.get('text'):
                    # Simple HTML to text conversion
                    import re
                    text = re.sub(r'<[^>]+>', '', email_data['html'])
                    email_data['text'] = text.strip()

                # Send via Resend API
                headers = {
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json',
                }
                
                logger.info(f"Sending email via Resend to {email_data['to']}")
                
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    json=email_data,
                    timeout=30
                )
                
                if response.status_code == 200:
                    logger.info(f"✅ Email sent successfully via Resend to {email_data['to']}")
                    sent_count += 1
                else:
                    error_msg = f"Resend API error: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    
                    # If domain verification issue, try with Resend's verified domain
                    if response.status_code == 403 and 'domain is not verified' in response.text:
                        logger.info("Retrying with Resend verified domain...")
                        email_data['from'] = 'onboarding@resend.dev'
                        
                        retry_response = requests.post(
                            self.api_url,
                            headers=headers,
                            json=email_data,
                            timeout=30
                        )
                        
                        if retry_response.status_code == 200:
                            logger.info(f"✅ Email sent via Resend (retry) to {email_data['to']}")
                            sent_count += 1
                        else:
                            logger.error(f"Retry failed: {retry_response.status_code} - {retry_response.text}")
                            if not self.fail_silently:
                                raise Exception(f"Resend retry failed: {retry_response.text}")
                    else:
                        if not self.fail_silently:
                            raise Exception(error_msg)

            except Exception as e:
                logger.error(f"Failed to send email via Resend: {str(e)}")
                if not self.fail_silently:
                    raise

        return sent_count


class SendGridEmailBackend(BaseEmailBackend):
    """
    Alternative email backend using SendGrid API
    
    SendGrid is also Railway-friendly and has a generous free tier.
    Free tier: 100 emails/day, which should be enough for basic OTP needs.
    """

    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently, **kwargs)
        self.api_key = getattr(settings, 'SENDGRID_API_KEY', '')
        self.api_url = 'https://api.sendgrid.com/v3/mail/send'

    def send_messages(self, email_messages):
        """Send email messages using SendGrid API"""
        if not self.api_key:
            logger.error("SENDGRID_API_KEY not configured")
            if not self.fail_silently:
                raise ValueError("SENDGRID_API_KEY not configured")
            return 0

        sent_count = 0
        
        for message in email_messages:
            try:
                # Prepare email data for SendGrid API
                email_data = {
                    'personalizations': [{
                        'to': [{'email': email} for email in message.to],
                        'subject': message.subject
                    }],
                    'from': {'email': message.from_email or settings.DEFAULT_FROM_EMAIL},
                    'content': [{'type': 'text/plain', 'value': message.body}]
                }
                
                # Add HTML content if available
                if hasattr(message, 'alternatives') and message.alternatives:
                    for alternative in message.alternatives:
                        if alternative[1] == 'text/html':
                            email_data['content'].append({
                                'type': 'text/html', 
                                'value': alternative[0]
                            })

                headers = {
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json',
                }
                
                logger.info(f"Sending email via SendGrid to {message.to}")
                
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    json=email_data,
                    timeout=30
                )
                
                if response.status_code == 202:  # SendGrid returns 202 for success
                    logger.info(f"✅ Email sent successfully via SendGrid to {message.to}")
                    sent_count += 1
                else:
                    error_msg = f"SendGrid API error: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    if not self.fail_silently:
                        raise Exception(error_msg)

            except Exception as e:
                logger.error(f"Failed to send email via SendGrid: {str(e)}")
                if not self.fail_silently:
                    raise

        return sent_count


class RailwayCompatibleEmailBackend(BaseEmailBackend):
    """
    Smart email backend that tries multiple services in order:
    1. Resend (if API key available)
    2. SendGrid (if API key available)  
    3. SMTP (if credentials available)
    4. Console (fallback)
    """

    def send_messages(self, email_messages):
        """Try multiple email services in order of preference"""
        
        # Try Resend first (recommended for Railway)
        if getattr(settings, 'RESEND_API_KEY', ''):
            try:
                backend = ResendEmailBackend()
                return backend.send_messages(email_messages)
            except Exception as e:
                logger.warning(f"Resend backend failed: {e}")
        
        # Try SendGrid second
        if getattr(settings, 'SENDGRID_API_KEY', ''):
            try:
                backend = SendGridEmailBackend()
                return backend.send_messages(email_messages)
            except Exception as e:
                logger.warning(f"SendGrid backend failed: {e}")
        
        # Try SMTP third (may be blocked)
        if getattr(settings, 'EMAIL_HOST_USER', '') and getattr(settings, 'EMAIL_HOST_PASSWORD', ''):
            try:
                from django.core.mail.backends.smtp import EmailBackend
                backend = EmailBackend()
                return backend.send_messages(email_messages)
            except Exception as e:
                logger.warning(f"SMTP backend failed: {e}")
        
        # Console fallback
        logger.warning("All email backends failed, using console fallback")
        from django.core.mail.backends.console import EmailBackend
        backend = EmailBackend()
        return backend.send_messages(email_messages)