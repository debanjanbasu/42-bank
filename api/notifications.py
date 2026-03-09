"""
Push Notifications API for Mobile App.

Integrates with Azure Notification Hubs to send push notifications
to iOS and Android devices.

Supports:
- Transaction notifications (money sent/received)
- Payment request notifications
- Security alerts (new device login)
- Account updates

Development:
- Use Expo Push Notifications for local testing
- Azure Notification Hubs for production

Endpoints:
    POST /api/notifications/register - Register device push token
    DELETE /api/notifications/register - Unregister device
    POST /api/notifications/send - Send notification (internal)
"""

import os
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, Field

from api.deps import get_current_user

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


# ============ Configuration ============

# Azure Notification Hubs (Production)
AZURE_NOTIFICATION_HUB_CONNECTION_STRING = os.getenv("AZURE_NOTIFICATION_HUB_CONNECTION_STRING")
AZURE_NOTIFICATION_HUB_NAME = os.getenv("AZURE_NOTIFICATION_HUB_NAME")

# Expo Push Notifications (Development)
EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"

# Enable development mode (Expo) if no Azure config
USE_EXPO = not AZURE_NOTIFICATION_HUB_CONNECTION_STRING


# ============ Request/Response Models ============

class RegisterPushTokenRequest(BaseModel):
    """Register push notification token."""
    push_token: str = Field(..., description="Expo push token or APNs/FCM token")
    platform: str = Field(..., description="ios, android, or expo")
    device_id: str = Field(..., description="Device identifier")
    device_name: Optional[str] = Field(None, description="User-friendly device name")


class RegisterPushTokenResponse(BaseModel):
    """Registration confirmation."""
    status: str
    push_token: str
    platform: str


class SendNotificationRequest(BaseModel):
    """Send notification to user (internal use)."""
    user_id: str
    title: str
    body: str
    data: Optional[Dict[str, Any]] = None
    notification_type: str = Field(
        default="general",
        description="Type: transaction, request, security, general"
    )


class SendNotificationResponse(BaseModel):
    """Notification send result."""
    status: str
    message_id: Optional[str] = None
    error: Optional[str] = None


class NotificationPreferences(BaseModel):
    """User notification preferences."""
    transactions: bool = True
    payment_requests: bool = True
    security_alerts: bool = True
    marketing: bool = False


class NotificationHistory(BaseModel):
    """Notification history for user."""
    notifications: List[Dict[str, Any]]
    total: int


# ============ In-Memory Storage (Replace with Cosmos DB) ============

# Structure: { user_token: [{ push_token, platform, device_id, registered_at }] }
_push_tokens: Dict[str, List[Dict[str, Any]]] = {}

# Structure: { notification_id: { user_id, title, body, data, sent_at, status } }
_notification_history: Dict[str, Dict[str, Any]] = {}


# ============ Helper Functions ============


async def send_expo_push_notification(
    push_token: str,
    title: str,
    body: str,
    data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Send push notification via Expo.
    
    Used in development mode.
    
    Args:
        push_token: Expo push token (ExponentPushToken[xxx])
        title: Notification title
        body: Notification body
        data: Additional data payload
        
    Returns:
        Response from Expo push service
    """
    import httpx
    
    message = {
        "to": push_token,
        "title": title,
        "body": body,
        "data": data or {},
        "sound": "default",
        "priority": "high",
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            EXPO_PUSH_URL,
            json=message,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            return {
                "status": "success",
                "message_id": result.get("data", {}).get("id"),
            }
        else:
            return {
                "status": "failed",
                "error": response.text,
            }


async def send_azure_push_notification(
    push_token: str,
    platform: str,
    title: str,
    body: str,
    data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Send push notification via Azure Notification Hubs.
    
    Used in production.
    
    Args:
        push_token: APNs or FCM token
        platform: "ios" or "android"
        title: Notification title
        body: Notification body
        data: Additional data payload
        
    Returns:
        Response from Azure Notification Hubs
    """
    # TODO: Implement Azure Notification Hubs SDK
    # For now, fall back to Expo
    return await send_expo_push_notification(push_token, title, body, data)


async def send_notification_to_user(
    user_id: str,
    title: str,
    body: str,
    data: Optional[Dict[str, Any]] = None,
    notification_type: str = "general"
) -> List[Dict[str, Any]]:
    """
    Send notification to all registered devices for a user.
    
    Args:
        user_id: User token
        title: Notification title
        body: Notification body
        data: Additional data payload
        notification_type: Type of notification
        
    Returns:
        List of send results for each device
    """
    devices = _push_tokens.get(user_id, [])
    
    if not devices:
        return [{"status": "no_devices", "error": "No devices registered"}]
    
    results = []
    
    for device in devices:
        push_token = device["push_token"]
        platform = device["platform"]
        
        if USE_EXPO or platform == "expo":
            result = await send_expo_push_notification(push_token, title, body, data)
        else:
            result = await send_azure_push_notification(push_token, platform, title, body, data)
        
        results.append({
            "device_id": device["device_id"],
            **result
        })
    
    # Store in history
    notification_id = f"notif_{datetime.utcnow().timestamp()}"
    _notification_history[notification_id] = {
        "user_id": user_id,
        "title": title,
        "body": body,
        "data": data,
        "notification_type": notification_type,
        "sent_at": datetime.utcnow().isoformat(),
        "results": results,
    }
    
    return results


# ============ Endpoints ============

@router.post("/register", response_model=RegisterPushTokenResponse)
async def register_push_token(
    request: RegisterPushTokenRequest,
    user: dict = Depends(get_current_user)
):
    """
    Register device push token for notifications.
    
    Mobile app calls this after obtaining push token:
    - iOS: APNs device token
    - Android: FCM registration token
    - Expo: ExponentPushToken[xxx]
    
    Args:
        request: Push token registration data
        
    Returns:
        Registration confirmation
    """
    user_token = user["sub"]
    
    # Initialize user's device list if needed
    if user_token not in _push_tokens:
        _push_tokens[user_token] = []
    
    # Check if device already registered
    devices = _push_tokens[user_token]
    existing = next(
        (d for d in devices if d["device_id"] == request.device_id),
        None
    )
    
    if existing:
        # Update existing registration
        existing["push_token"] = request.push_token
        existing["platform"] = request.platform
        existing["updated_at"] = datetime.utcnow().isoformat()
    else:
        # Add new registration
        devices.append({
            "push_token": request.push_token,
            "platform": request.platform,
            "device_id": request.device_id,
            "device_name": request.device_name,
            "registered_at": datetime.utcnow().isoformat(),
        })
    
    return RegisterPushTokenResponse(
        status="registered",
        push_token=request.push_token,
        platform=request.platform,
    )


@router.delete("/register")
async def unregister_push_token(
    device_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Unregister device from push notifications.
    
    Call this when user logs out or disables notifications.
    """
    user_token = user["sub"]
    
    if user_token in _push_tokens:
        _push_tokens[user_token] = [
            d for d in _push_tokens[user_token]
            if d["device_id"] != device_id
        ]
    
    return {"status": "unregistered", "device_id": device_id}


@router.post("/send", response_model=SendNotificationResponse)
async def send_notification(
    request: SendNotificationRequest,
    internal_api_key: str = Header(None, alias="X-Internal-API-Key")
):
    """
    Send push notification to user.
    
    This endpoint is for internal use by other services
    (e.g., transaction service, auth service).
    
    Requires X-Internal-API-Key header for authentication.
    """
    # Validate internal API key
    expected_key = os.getenv("INTERNAL_API_KEY", "dev-internal-key")
    if internal_api_key != expected_key:
        raise HTTPException(403, "Invalid internal API key")
    
    # Send notification in background
    results = await send_notification_to_user(
        request.user_id,
        request.title,
        request.body,
        request.data,
        request.notification_type
    )
    
    # Check if any succeeded
    success = any(r.get("status") == "success" for r in results)
    
    return SendNotificationResponse(
        status="success" if success else "partial_failure",
        message_id=f"batch_{datetime.utcnow().timestamp()}",
        error=None if success else "Some devices failed",
    )


@router.get("/history", response_model=NotificationHistory)
async def get_notification_history(
    limit: int = 50,
    user: dict = Depends(get_current_user)
):
    """
    Get notification history for current user.
    
    Returns list of recent notifications sent to this user.
    """
    user_token = user["sub"]
    
    # Filter history for this user
    user_notifications = [
        {**notif, "id": notif_id}
        for notif_id, notif in _notification_history.items()
        if notif["user_id"] == user_token
    ]
    
    # Sort by sent_at descending
    user_notifications.sort(
        key=lambda x: x.get("sent_at", ""),
        reverse=True
    )
    
    return NotificationHistory(
        notifications=user_notifications[:limit],
        total=len(user_notifications),
    )


@router.get("/preferences", response_model=NotificationPreferences)
async def get_notification_preferences(
    user: dict = Depends(get_current_user)
):
    """
    Get user's notification preferences.
    
    Users can customize which types of notifications they receive.
    """
    # TODO: Load from database
    return NotificationPreferences()


@router.put("/preferences", response_model=NotificationPreferences)
async def update_notification_preferences(
    preferences: NotificationPreferences,
    user: dict = Depends(get_current_user)
):
    """
    Update notification preferences.
    
    Users can toggle different notification types.
    """
    # TODO: Save to database
    return preferences


@router.post("/test")
async def send_test_notification(
    user: dict = Depends(get_current_user)
):
    """
    Send test notification to verify setup.
    
    Useful during development to confirm push notifications work.
    """
    user_token = user["sub"]
    
    results = await send_notification_to_user(
        user_token,
        "Test Notification",
        "This is a test from 42-Bank!",
        {"type": "test", "timestamp": datetime.utcnow().isoformat()},
        "general"
    )
    
    return {
        "status": "sent",
        "devices": len(results),
        "results": results,
    }


# ============ Notification Helpers for Other Services ============

async def notify_transaction_received(
    recipient_user_id: str,
    sender_username: str,
    amount: float,
    description: str
):
    """
    Send notification for received transaction.
    
    Called by transaction service when user receives money.
    """
    return await send_notification_to_user(
        recipient_user_id,
        f"💰 Money Received",
        f"${amount:.2f} from {sender_username}: {description}",
        {
            "type": "transaction_received",
            "sender": sender_username,
            "amount": amount,
        },
        "transaction"
    )


async def notify_payment_request(
    recipient_user_id: str,
    requester_username: str,
    amount: float,
    description: str,
    request_id: str
):
    """
    Send notification for payment request.
    
    Called by transaction service when someone requests payment.
    """
    return await send_notification_to_user(
        recipient_user_id,
        f"💵 Payment Request",
        f"{requester_username} requests ${amount:.2f}: {description}",
        {
            "type": "payment_request",
            "requester": requester_username,
            "amount": amount,
            "request_id": request_id,
        },
        "request"
    )


async def notify_new_device_login(
    user_id: str,
    device_name: str,
    location: str
):
    """
    Send security alert for new device login.
    
    Called by auth service when user logs in from new device.
    """
    return await send_notification_to_user(
        user_id,
        "🔒 New Device Login",
        f"{device_name} from {location}",
        {
            "type": "security_alert",
            "device": device_name,
            "location": location,
        },
        "security"
    )
