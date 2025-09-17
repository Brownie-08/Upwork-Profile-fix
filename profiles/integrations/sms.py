import os


def send_sms(to: str, text: str) -> None:
    """
    Send SMS to a phone number.

    Args:
        to (str): Phone number to send SMS to
        text (str): SMS message text
    """
    api_key = os.getenv("SMS_API_KEY")
    sender = os.getenv("SMS_SENDER", "APP")

    if not api_key:
        # Dev no-op: log instead of sending
        print(f"[DEV SMS] To: {to} | From: {sender} | {text}")
        return

    # TODO: implement real vendor call (Twilio, Termii, etc.)
    # For now, just log even if API key is present
    print(f"[SMS] To: {to} | From: {sender} | {text}")
