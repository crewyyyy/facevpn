import json
import logging
import os
from typing import Optional, Tuple, Any, Dict

from aiohttp import ClientSession, ClientTimeout, ClientError

logger = logging.getLogger(__name__)

REMNIWAVE_API_URL = os.getenv("REMNIWAVE_API_URL", "").rstrip("/")
REMNIWAVE_API_KEY = os.getenv("REMNIWAVE_API_KEY")

_CLIENT_TIMEOUT = ClientTimeout(total=20)


def _build_headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {REMNIWAVE_API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _is_configured() -> bool:
    if not REMNIWAVE_API_URL or not REMNIWAVE_API_KEY:
        logger.error("Remniwave API is not configured. Check REMNIWAVE_API_URL and REMNIWAVE_API_KEY.")
        return False
    return True


async def create_subscription(
    customer_reference: str,
    plan_code: str,
    amount: float,
    currency: str = "RUB",
) -> Tuple[Optional[str], Optional[str]]:
    """
    Creates subscription in Remniwave and returns (checkout_url, subscription_id).
    """
    if not _is_configured():
        return None, None

    payload = {
        "plan_code": plan_code,
        "customer_reference": customer_reference,
        "currency": currency,
        "amount": amount,
    }

    try:
        async with ClientSession(timeout=_CLIENT_TIMEOUT) as session:
            async with session.post(
                f"{REMNIWAVE_API_URL}/subscriptions",
                data=json.dumps(payload),
                headers=_build_headers(),
            ) as response:
                text = await response.text()
                logger.debug("Remniwave subscription response (%s): %s", response.status, text)
                if response.status >= 400:
                    logger.error("Failed to create subscription: %s", text)
                    return None, None
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    logger.error("Unable to decode Remniwave response.")
                    return None, None
                return data.get("checkout_url"), data.get("id") or data.get("subscription_id")
    except ClientError as exc:
        logger.error("Remniwave request error: %s", exc)
        return None, None


async def get_subscription_status(subscription_id: str) -> Optional[Dict[str, Any]]:
    """
    Returns detailed subscription data for the given identifier.
    """
    if not _is_configured():
        return None

    try:
        async with ClientSession(timeout=_CLIENT_TIMEOUT) as session:
            async with session.get(
                f"{REMNIWAVE_API_URL}/subscriptions/{subscription_id}",
                headers=_build_headers(),
            ) as response:
                text = await response.text()
                logger.debug("Remniwave status response (%s): %s", response.status, text)
                if response.status >= 400:
                    logger.error("Failed to fetch subscription status: %s", text)
                    return None
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    logger.error("Unable to decode Remniwave status response.")
                    return None
    except ClientError as exc:
        logger.error("Remniwave status request error: %s", exc)
    return None

