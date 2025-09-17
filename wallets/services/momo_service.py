import uuid
import requests
from django.conf import settings
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
import logging

logger = logging.getLogger(__name__)


class MTNMoMoService:
    def __init__(self):
        self.base_url = settings.MTN_MOMO_CONFIG["BASE_URL"]
        self.subscription_key = settings.MTN_MOMO_CONFIG["SUBSCRIPTION_KEY"]
        self.api_user_id = settings.MTN_MOMO_CONFIG.get("API_USER_ID")
        self.api_key = settings.MTN_MOMO_CONFIG.get("API_KEY")
        self.callback_url = settings.MTN_MOMO_CONFIG.get("CALLBACK_URL")
        self.environment = settings.MTN_MOMO_CONFIG.get("ENVIRONMENT", "sandbox")
        self.currency = settings.MTN_MOMO_CONFIG.get("CURRENCY", "SZL")

    def setup_api_user(self):
        """Create an API user and generate an API key."""
        api_user_id = str(uuid.uuid4())
        headers = {
            "Ocp-Apim-Subscription-Key": self.subscription_key,
            "Content-Type": "application/json",
            "X-Reference-Id": api_user_id,
        }
        payload = {
            "providerCallbackHost": settings.MTN_MOMO_CONFIG.get(
                "PROVIDER_CALLBACK_HOST", "yourdomain.com"
            )
        }
        url = f"{self.base_url}/v1_0/apiuser"

        try:
            response = requests.post(url, headers=headers, json=payload)
            logger.debug(
                f"API user creation request: {url}, Headers: {headers}, Payload: {payload}"
            )
            logger.debug(
                f"API user creation response: {response.status_code}, {response.text}"
            )

            if response.status_code == 201:
                # Create API key for the user
                key_response = self._create_api_key(api_user_id)
                if key_response["success"]:
                    return {
                        "success": True,
                        "api_user_id": api_user_id,
                        "api_key": key_response["api_key"],
                    }
                else:
                    return {"success": False, "message": key_response["message"]}
            else:
                error_message = response.text or f"HTTP {response.status_code}"
                try:
                    error_json = response.json()
                    error_message = error_json.get("message", error_message)
                except ValueError:
                    pass
                return {
                    "success": False,
                    "message": f"Failed to create API user: {error_message}",
                }
        except requests.RequestException as e:
            logger.error(f"API user creation failed: {str(e)}")
            return {"success": False, "message": f"Request failed: {str(e)}"}

    def _create_api_key(self, api_user_id):
        """Generate an API key for the given API user."""
        url = f"{self.base_url}/v1_0/apiuser/{api_user_id}/apikey"
        headers = {
            "Ocp-Apim-Subscription-Key": self.subscription_key,
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(url, headers=headers)
            logger.debug(f"API key creation request: {url}, Headers: {headers}")
            logger.debug(
                f"API key creation response: {response.status_code}, {response.text}"
            )

            if response.status_code == 201:
                data = response.json()
                return {"success": True, "api_key": data.get("apiKey")}
            else:
                error_message = response.text or f"HTTP {response.status_code}"
                try:
                    error_json = response.json()
                    error_message = error_json.get("message", error_message)
                except ValueError:
                    pass
                return {
                    "success": False,
                    "message": f"Failed to create API key: {error_message}",
                }
        except requests.RequestException as e:
            logger.error(f"API key creation failed: {str(e)}")
            return {"success": False, "message": f"Request failed: {str(e)}"}

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(2),
        retry=retry_if_exception_type(requests.RequestException),
    )
    def request_to_pay(
        self, amount, phone_number, external_id, currency, payer_message, payee_note
    ):
        """Initiate a request-to-pay transaction."""
        access_token = self._get_access_token()
        if not access_token:
            return {"success": False, "message": "Failed to obtain access token"}

        url = f"{self.base_url}/collection/v1_0/requesttopay"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Ocp-Apim-Subscription-Key": self.subscription_key,
            "X-Reference-Id": external_id,
            "X-Target-Environment": self.environment,
            "Content-Type": "application/json",
        }
        payload = {
            "amount": str(amount),
            "currency": currency,
            "externalId": external_id,
            "payer": {
                "partyIdType": "MSISDN",
                "partyId": phone_number.lstrip("+"),  # Remove + for MoMo API
            },
            "payerMessage": payer_message,
            "payeeNote": payee_note,
        }

        try:
            response = requests.post(url, headers=headers, json=payload)
            logger.debug(
                f"Request to pay: {url}, Headers: {headers}, Payload: {payload}"
            )
            logger.debug(
                f"Request to pay response: {response.status_code}, {response.text}"
            )

            if response.status_code == 202:
                return {"success": True, "reference_id": external_id}
            else:
                error_message = response.text or f"HTTP {response.status_code}"
                try:
                    error_json = response.json()
                    error_message = error_json.get("message", error_message)
                except ValueError:
                    pass
                return {"success": False, "message": error_message}
        except requests.RequestException as e:
            logger.error(f"Request to pay failed: {str(e)}")
            return {"success": False, "message": str(e)}

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(2),
        retry=retry_if_exception_type(requests.RequestException),
    )
    def transfer_money(
        self, amount, phone_number, external_id, currency, payee_message, payer_note
    ):
        """Initiate a disbursement transfer."""
        access_token = self._get_access_token()
        if not access_token:
            return {"success": False, "message": "Failed to obtain access token"}

        url = f"{self.base_url}/disbursement/v1_0/transfer"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Ocp-Apim-Subscription-Key": self.subscription_key,
            "X-Reference-Id": external_id,
            "X-Target-Environment": self.environment,
            "Content-Type": "application/json",
        }
        payload = {
            "amount": str(amount),
            "currency": currency,
            "externalId": external_id,
            "payee": {
                "partyIdType": "MSISDN",
                "partyId": phone_number.lstrip("+"),  # Remove + for MoMo API
            },
            "payerMessage": payer_note,
            "payeeNote": payee_message,
        }

        try:
            response = requests.post(url, headers=headers, json=payload)
            logger.debug(
                f"Transfer money: {url}, Headers: {headers}, Payload: {payload}"
            )
            logger.debug(
                f"Transfer money response: {response.status_code}, {response.text}"
            )

            if response.status_code == 202:
                return {"success": True, "reference_id": external_id}
            else:
                error_message = response.text or f"HTTP {response.status_code}"
                try:
                    error_json = response.json()
                    error_message = error_json.get("message", error_message)
                except ValueError:
                    pass
                return {"success": False, "message": error_message}
        except requests.RequestException as e:
            logger.error(f"Transfer money failed: {str(e)}")
            return {"success": False, "message": str(e)}

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(2),
        retry=retry_if_exception_type(requests.RequestException),
    )
    def get_transaction_status(self, transaction_id):
        """Check the status of a transaction."""
        access_token = self._get_access_token()
        if not access_token:
            return {"success": False, "message": "Failed to obtain access token"}

        url = f"{self.base_url}/collection/v1_0/requesttopay/{transaction_id}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Ocp-Apim-Subscription-Key": self.subscription_key,
            "X-Target-Environment": self.environment,
            "Content-Type": "application/json",
        }

        try:
            response = requests.get(url, headers=headers)
            logger.debug(f"Transaction status: {url}, Headers: {headers}")
            logger.debug(
                f"Transaction status response: {response.status_code}, {response.text}"
            )

            if response.status_code == 200:
                data = response.json()
                return {"success": True, "data": data}
            else:
                error_message = response.text or f"HTTP {response.status_code}"
                try:
                    error_json = response.json()
                    error_message = error_json.get("message", error_message)
                except ValueError:
                    pass
                return {"success": False, "message": error_message}
        except requests.RequestException as e:
            logger.error(f"Transaction status check failed: {str(e)}")
            return {"success": False, "message": str(e)}

    def _get_access_token(self):
        """Obtain an access token for API requests."""
        url = f"{self.base_url}/collection/token/"
        auth = (self.api_user_id, self.api_key)
        headers = {
            "Ocp-Apim-Subscription-Key": self.subscription_key,
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(url, auth=auth, headers=headers)
            logger.debug(f"Access token request: {url}, Headers: {headers}")
            logger.debug(
                f"Access token response: {response.status_code}, {response.text}"
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("access_token")
            else:
                error_message = response.text or f"HTTP {response.status_code}"
                try:
                    error_json = response.json()
                    error_message = error_json.get("message", error_message)
                except ValueError:
                    pass
                logger.error(f"Failed to get access token: {error_message}")
                return None
        except requests.RequestException as e:
            logger.error(f"Access token request failed: {str(e)}")
            return None
