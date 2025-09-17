from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import transaction
from django.views.decorators.http import require_POST
from django.db.models import Q, Count, Max, Prefetch
from django.utils import timezone
from .models import ChatRoom, Message, ProjectMilestone
from projects.models import Project
from notifications.models import Notification


@login_required
def chatroom_list(request):
    user_role = "client" if hasattr(request.user, "client_profile") else "freelancer"

    chatrooms = (
        ChatRoom.objects.filter(
            Q(client=request.user) | Q(freelancer=request.user), is_active=True
        )
        .annotate(
            unread_count=Count(
                "messages",
                filter=Q(messages__is_read=False) & ~Q(messages__sender=request.user),
            ),
            last_message_time=Max("messages__timestamp"),
            pending_milestones=Count(
                "milestones",
                filter=Q(milestones__is_completed=False)
                & Q(milestones__due_date__gt=timezone.now()),
            ),
        )
        .select_related("project", "client", "freelancer", "last_milestone_message")
        .prefetch_related(
            Prefetch(
                "messages",
                queryset=Message.objects.filter(is_read=False),
                to_attr="unread_messages",
            )
        )
        .order_by("-last_message_time")
    )

    context = {"chatrooms": chatrooms, "user_role": user_role}
    return render(request, "chat/chatroom_list.html", context)


@login_required
def chatroom(request, chatroom_id=None, project_id=None):
    if chatroom_id:
        chatroom = get_object_or_404(
            ChatRoom.objects.select_related(
                "project", "client", "freelancer", "last_milestone_message"
            ),
            id=chatroom_id,
        )
    elif project_id:
        project = get_object_or_404(Project, id=project_id)
        chatroom, created = ChatRoom.objects.get_or_create(
            project=project, client=project.client, freelancer=project.freelancer
        )
        if created:
            Message.objects.create(
                chatroom=chatroom,
                sender=request.user,
                content="Welcome to the chatroom!",
                message_type="REGULAR",
            )
    else:
        return redirect("chatroom_list")

    if request.user not in [chatroom.client, chatroom.freelancer]:
        return redirect("chatroom_list")

    user_role = "client" if request.user == chatroom.client else "freelancer"

    messages = (
        chatroom.messages.select_related(
            "sender", "related_milestone", "related_proposal"
        )
        .prefetch_related("attachments")
        .order_by("timestamp")
    )

    project = chatroom.project
    proposals = project.proposals.filter(
        Q(accepted=True) | Q(freelancer=chatroom.freelancer)
    ).select_related("freelancer")

    milestones = chatroom.milestones.prefetch_related(
        "associated_files", "related_messages"
    ).order_by("due_date")

    if chatroom.project_status != project.status:
        chatroom.sync_project_status()

    context = {
        "chatroom": chatroom,
        "messages": messages,
        "pinned_messages": messages.filter(is_pinned=True),
        "milestones": milestones,
        "project": project,
        "proposals": proposals,
        "user_role": user_role,
    }

    with transaction.atomic():
        Message.objects.filter(chatroom=chatroom, is_read=False).exclude(
            sender=request.user
        ).update(is_read=True)

        Notification.objects.filter(
            chat_message__chatroom=chatroom, user=request.user, is_read=False
        ).update(is_read=True)

    return render(request, "chat/chatroom.html", context)


@login_required
@require_POST
def create_milestone(request, chatroom_id):
    chatroom = get_object_or_404(ChatRoom, id=chatroom_id)

    if request.user != chatroom.client:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    with transaction.atomic():
        milestone = ProjectMilestone.objects.create(
            chatroom=chatroom,
            title=request.POST["title"],
            description=request.POST["description"],
            due_date=request.POST["due_date"],
            amount=request.POST["amount"],
        )

        message = Message.objects.create(
            chatroom=chatroom,
            sender=request.user,
            content=f"Created milestone: {milestone.title}",
            message_type="MILESTONE",
            related_milestone=milestone,
        )

        chatroom.last_milestone_message = message
        chatroom.save()

    return JsonResponse(
        {"success": True, "milestone_id": milestone.id, "message_id": message.id}
    )


@login_required
@require_POST
def complete_milestone(request, milestone_id):
    milestone = get_object_or_404(ProjectMilestone, id=milestone_id)

    if request.user != milestone.chatroom.freelancer:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    with transaction.atomic():
        milestone.mark_as_completed()

    return JsonResponse({"success": True})


@login_required
@require_POST
def pin_message(request, message_id):
    message = get_object_or_404(
        Message.objects.select_related("chatroom"), id=message_id
    )

    if request.user not in [message.chatroom.client, message.chatroom.freelancer]:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    message.is_pinned = not message.is_pinned
    message.save()

    return JsonResponse({"success": True, "is_pinned": message.is_pinned})


@login_required
@require_POST
def handle_project_status_change(request, chatroom_id):
    chatroom = get_object_or_404(ChatRoom, id=chatroom_id)
    new_status = request.POST.get("status")

    if request.user not in [chatroom.client, chatroom.freelancer]:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    with transaction.atomic():
        chatroom.project.status = new_status
        chatroom.project.save()

        chatroom.sync_project_status()

        Message.objects.create(
            chatroom=chatroom,
            sender=request.user,
            content=f"Project status updated to: {new_status}",
            message_type="STATUS_CHANGE",
        )

    return JsonResponse({"success": True})
