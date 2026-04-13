"""NovaPay Bank API — Webhook/Notification Routes
VULN: Server Side Request Forgery / SSRF (API7)
"""
from fastapi import APIRouter, Depends
import httpx

from app.schemas import WebhookRequest
from app.auth import get_current_user

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


@router.post("/webhook")
async def register_webhook(
    req: WebhookRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Register a webhook URL for payment notifications.

    VULN API7:2023 — Server Side Request Forgery (SSRF):
    The server makes an HTTP request to the user-supplied URL without any validation.
    An attacker can point it to internal services.

    Try: {"url": "http://169.254.169.254/latest/meta-data/", "event": "payment_received"}
    Try: {"url": "http://localhost:8080/api/admin/stats", "event": "test"}
    Try: {"url": "http://127.0.0.1:22", "event": "port_scan"}
    """
    # VULN: No URL validation — allows internal network access
    try:
        async with httpx.AsyncClient(timeout=5.0, verify=False) as client:
            response = await client.get(req.url)
            return {
                "message": "Webhook URL verified successfully",
                "url": req.url,
                "event": req.event,
                "verification_status": response.status_code,
                "verification_response": response.text[:500],  # VULN: Returns internal response body
            }
    except httpx.ConnectError:
        return {
            "message": "Webhook URL verification failed — connection refused",
            "url": req.url,
            "event": req.event,
            "verification_status": "connection_refused",
            # VULN: Confirms the host exists but port is closed — useful for port scanning
        }
    except httpx.TimeoutException:
        return {
            "message": "Webhook URL verification — timeout (host may be unreachable)",
            "url": req.url,
            "verification_status": "timeout",
        }
    except Exception as e:
        return {
            "message": "Webhook URL verification failed",
            "url": req.url,
            "error": str(e),  # VULN: Leaks internal error details
        }
