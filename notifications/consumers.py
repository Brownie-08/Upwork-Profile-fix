import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)


class AdminNotificationConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time admin notifications."""

    async def connect(self):
        """Handle WebSocket connection."""
        # Get user from session
        user = self.scope.get("user")

        # Only allow staff users to connect
        if user and user.is_authenticated and (user.is_staff or user.is_superuser):
            # Join the admins group
            self.group_name = "admins"
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()

            logger.info(
                f"Admin user {user.username} connected to notifications WebSocket"
            )

            # Send initial connection confirmation
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "connection_established",
                        "message": "Connected to admin notifications",
                        "user": user.username,
                    }
                )
            )
        else:
            # Reject connection for non-admin users
            logger.warning(
                f"Non-admin user attempted to connect to admin notifications: {user}"
            )
            await self.close(code=4001)  # Custom close code for unauthorized access

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        user = self.scope.get("user")
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

        logger.info(
            f"Admin user {user.username if user else 'Unknown'} disconnected from notifications WebSocket (code: {close_code})"
        )

    async def receive(self, text_data):
        """Handle messages from WebSocket (not used for notifications, but required by interface)."""
        try:
            data = json.loads(text_data)
            message_type = data.get("type", "")

            # Handle ping/pong for connection keep-alive
            if message_type == "ping":
                await self.send(
                    text_data=json.dumps(
                        {"type": "pong", "timestamp": data.get("timestamp")}
                    )
                )

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received from WebSocket: {text_data}")
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {str(e)}")

    async def notification_message(self, event):
        """Handle notification messages from the group."""
        try:
            # Send the notification to the WebSocket
            await self.send(text_data=json.dumps(event["payload"]))
            logger.debug(
                f"Sent notification to admin: {event['payload']['notification_type']}"
            )
        except Exception as e:
            logger.error(f"Error sending notification to WebSocket: {str(e)}")

    @database_sync_to_async
    def get_user_notifications_count(self, user):
        """Get the unread notifications count for a user."""
        try:
            from .models import Notification

            return Notification.objects.filter(user=user, is_read=False).count()
        except Exception as e:
            logger.error(f"Error getting notifications count: {str(e)}")
            return 0
