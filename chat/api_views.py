from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET
from django.core.exceptions import PermissionDenied
from django.http import FileResponse
from .models import ChatRoom, Message, MessageAttachment
from django.db.models import Q
import json


@login_required
@require_POST
def send_message(request):
    try:
        data = json.loads(request.body)
        chatroom = get_object_or_404(ChatRoom, id=data.get("chatroom_id"))

        # Verify user is part of the chat
        if request.user not in [chatroom.client, chatroom.freelancer]:
            raise PermissionDenied

        message = Message.objects.create(
            chatroom=chatroom,
            sender=request.user,
            content=data.get("content"),
            message_type=data.get("message_type", "regular"),
        )

        return JsonResponse(
            {
                "id": message.id,
                "content": message.content,
                "timestamp": message.timestamp.isoformat(),
                "sender_id": message.sender.id,
                "sender_name": message.sender.get_full_name()
                or message.sender.username,
                "message_type": message.message_type,
            }
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_POST
def mark_messages_read(request):
    try:
        data = json.loads(request.body)
        chatroom = get_object_or_404(ChatRoom, id=data.get("chatroom_id"))

        if request.user not in [chatroom.client, chatroom.freelancer]:
            raise PermissionDenied

        # Mark all unread messages in this chat as read
        Message.objects.filter(chatroom=chatroom, is_read=False).exclude(
            sender=request.user
        ).update(is_read=True)

        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_POST
def upload_attachment(request):
    try:
        chatroom = get_object_or_404(ChatRoom, id=request.POST.get("chatroom_id"))

        if request.user not in [chatroom.client, chatroom.freelancer]:
            raise PermissionDenied

        attachments = []
        for file in request.FILES.getlist("files"):
            attachment = MessageAttachment.objects.create(
                chatroom=chatroom,
                uploaded_by=request.user,
                file=file,
                file_name=file.name,
                category=request.POST.get("category", "other"),
                description=request.POST.get("description", ""),
            )
            attachments.append(attachment.id)

        # Create message for attachments
        Message.objects.create(
            chatroom=chatroom,
            sender=request.user,
            content=f"Uploaded {len(attachments)} file(s)",
            message_type="attachment",
            has_attachment=True,
        )

        return JsonResponse({"success": True, "attachment_ids": attachments})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_GET
def serve_attachment(request, filename):
    attachment = get_object_or_404(MessageAttachment, file=filename)

    if request.user not in [attachment.chatroom.client, attachment.chatroom.freelancer]:
        raise PermissionDenied

    return FileResponse(attachment.file)


@login_required
@require_GET
def milestone_list(request):
    try:
        chatroom = get_object_or_404(ChatRoom, id=request.GET.get("chatroom_id"))

        if request.user not in [chatroom.client, chatroom.freelancer]:
            raise PermissionDenied

        milestones = chatroom.milestones.all().order_by("due_date")

        return JsonResponse(
            {
                "milestones": [
                    {
                        "id": milestone.id,
                        "title": milestone.title,
                        "description": milestone.description,
                        "amount": str(milestone.amount),
                        "due_date": milestone.due_date.isoformat(),
                        "is_completed": milestone.is_completed,
                        "completed_at": (
                            milestone.completed_at.isoformat()
                            if milestone.completed_at
                            else None
                        ),
                    }
                    for milestone in milestones
                ]
            }
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_GET
def chatroom_list(request):
    try:
        chatrooms = ChatRoom.objects.filter(
            Q(client=request.user) | Q(freelancer=request.user), is_active=True
        ).select_related("project", "client", "freelancer")

        return JsonResponse(
            {
                "chatrooms": [
                    {
                        "id": room.id,
                        "project_title": room.project.title,
                        "client_name": room.client.get_full_name()
                        or room.client.username,
                        "freelancer_name": room.freelancer.get_full_name()
                        or room.freelancer.username,
                        "last_message": (
                            room.messages.last().content
                            if room.messages.exists()
                            else None
                        ),
                        "unread_count": room.messages.filter(is_read=False)
                        .exclude(sender=request.user)
                        .count(),
                    }
                    for room in chatrooms
                ]
            }
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_GET
def chatroom_detail(request, chatroom_id):
    try:
        chatroom = get_object_or_404(ChatRoom, id=chatroom_id)

        if request.user not in [chatroom.client, chatroom.freelancer]:
            raise PermissionDenied

        return JsonResponse(
            {
                "id": chatroom.id,
                "project": {
                    "id": chatroom.project.id,
                    "title": chatroom.project.title,
                    "status": chatroom.project.status,
                    "budget": str(chatroom.project.budget),
                },
                "client": {
                    "id": chatroom.client.id,
                    "name": chatroom.client.get_full_name() or chatroom.client.username,
                },
                "freelancer": {
                    "id": chatroom.freelancer.id,
                    "name": chatroom.freelancer.get_full_name()
                    or chatroom.freelancer.username,
                },
                "messages": [
                    {
                        "id": msg.id,
                        "content": msg.content,
                        "sender_id": msg.sender.id,
                        "timestamp": msg.timestamp.isoformat(),
                        "is_read": msg.is_read,
                        "message_type": msg.message_type,
                        "has_attachment": msg.has_attachment,
                    }
                    for msg in chatroom.messages.all().order_by("timestamp")
                ],
            }
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)
