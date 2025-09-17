# SMS Service Integration Options for LusitoHub OTP

This document outlines different SMS service integrations for production use.

## 1. Twilio Integration (Recommended)

### Setup:
```bash
pip install twilio
```

### Settings Configuration:
```python
# settings.py
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN') 
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER')
```

### Environment Variables:
```env
TWILIO_ACCOUNT_SID=your_account_sid_here
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+1234567890
```

### Implementation (already set up in OTPService):
Uncomment the Twilio integration code in `profiles/services/otp.py`:

```python
from twilio.rest import Client
client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
message = client.messages.create(
    body=message,
    from_=settings.TWILIO_PHONE_NUMBER,
    to=phone
)
```

## 2. AWS SNS Integration

### Setup:
```bash
pip install boto3
```

### Settings Configuration:
```python
# settings.py
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
```

### Implementation:
Uncomment the AWS SNS code in `profiles/services/otp.py`:

```python
import boto3
sns = boto3.client('sns', region_name=settings.AWS_REGION)
response = sns.publish(PhoneNumber=phone, Message=message)
```

## 3. Africa's Talking (For African Markets)

### Setup:
```bash
pip install africastalking
```

### Implementation:
```python
import africastalking
africastalking.initialize(username='your_username', api_key='your_api_key')
sms = africastalking.SMS
response = sms.send(message, [phone])
```

## 4. Other SMS Providers

- **Nexmo (Vonage)**: Global SMS service
- **MessageBird**: International SMS API
- **Plivo**: Cloud communications platform
- **ClickSend**: SMS API service
- **Bulk SMS**: Various regional providers

## Production Deployment Steps:

1. Choose an SMS provider (Twilio recommended)
2. Sign up and get API credentials
3. Set environment variables
4. Update `profiles/services/otp.py`
5. Test with real phone numbers
6. Monitor delivery rates and costs

## Cost Considerations:

- **Twilio**: ~$0.0075 per SMS (US)
- **AWS SNS**: ~$0.00645 per SMS (US)
- **Africa's Talking**: Varies by country (typically lower cost for African markets)

## Security Notes:

- Never commit API keys to version control
- Use environment variables for all sensitive data
- Implement rate limiting to prevent abuse
- Monitor usage and set up billing alerts
- Consider two-factor authentication for SMS provider accounts

## Testing:

1. Set `SMS_BACKEND = 'development'` for console logging during development
2. Use test phone numbers provided by SMS services
3. Implement proper error handling for failed deliveries
4. Set up monitoring and alerting for production

## Implementation Status:

✅ Framework implemented in OTPService
✅ Twilio integration code ready (commented out)
✅ AWS SNS integration code ready (commented out)
⏸️ Choose provider and configure credentials
⏸️ Test with real phone numbers
⏸️ Deploy to production

Choose your preferred SMS provider and follow the setup instructions above!
