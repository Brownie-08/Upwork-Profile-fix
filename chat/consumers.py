import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ChatRoom, Message


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.room_group_name = f"chat_{self.room_id}"
        self.user = self.scope["user"]

        # Verify user has access to this chat room
        if not await self.user_has_access():
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get("type", "message")

        if message_type == "REGULAR":
            message = await self.save_message(data["message"])
            await self.channel_layer.group_send(
                self.room_group_name, {"type": "chat_message", "message": message}
            )
        elif message_type == "MILESTONE":
            milestone = await self.handle_milestone_update(data)
            await self.channel_layer.group_send(
                self.room_group_name,
                {"type": "milestone_update", "milestone": milestone},
            )

    @database_sync_to_async
    def user_has_access(self):
        try:
            chatroom = ChatRoom.objects.get(id=self.room_id)
            return self.user in [chatroom.client, chatroom.freelancer]
        except ChatRoom.DoesNotExist:
            return False

    @database_sync_to_async
    def save_message(self, message_content):
        chatroom = ChatRoom.objects.get(id=self.room_id)
        message = Message.objects.create(
            chatroom=chatroom, sender=self.user, content=message_content
        )
        return {
            "id": message.id,
            "content": message.content,
            "sender": message.sender.username,
            "timestamp": message.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        }

    async def chat_message(self, event):
        await self.send(
            text_data=json.dumps({"type": "message", "message": event["message"]})
        )

    async def milestone_update(self, event):
        await self.send(
            text_data=json.dumps(
                {"type": "milestone_update", "milestone": event["milestone"]}
            )
        )
