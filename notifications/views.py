from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Notification


@login_required
def notifications_page(request):
    notifications = Notification.objects.filter(user=request.user).order_by(
        "-created_at"
    )
    return render(
        request,
        "notifications/notifications.html",
        {
            "notifications": notifications,
        },
    )


@login_required
def get_unread_notifications(request):
    notifications = Notification.objects.filter(
        user=request.user, is_read=False
    ).order_by("-created_at")

    def get_valid_url(notification):
        """Get a valid URL for notification or fallback to safe default."""
        if notification.link:
            try:
                # Validate the URL by checking if referenced objects still exist
                if notification.project and "/room/" in notification.link:
                    # Check if the project's chatroom still exists
                    if hasattr(notification.project, "chatroom"):
                        return notification.link
                elif notification.transport_request:
                    # For transport notifications, return transport dashboard
                    return "/transport/dashboard/"
                elif notification.transaction:
                    # For wallet notifications, return wallet page
                    return "/wallet/"
                else:
                    # For other notifications, return the link if it exists
                    return notification.link
            except Exception:
                pass

        # Default fallback URLs based on notification type
        if notification.notification_type == "chat_message":
            return "/chatrooms/"
        elif "transport" in notification.notification_type:
            return "/transport/dashboard/"
        elif "wallet" in notification.notification_type:
            return "/wallet/"
        elif "project" in notification.notification_type:
            return "/projects/"
        else:
            return "/notifications/"  # Safe default

    data = [
        {
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "created_at": n.created_at.isoformat(),
            "is_read": n.is_read,
            "notification_type": n.notification_type,
            "url": get_valid_url(n),
        }
        for n in notifications
    ]
    return JsonResponse({"notifications": data})


@login_required
@require_POST
def mark_notification_read(request):
    # Support both form data and JSON body
    if request.content_type == "application/json":
        import json

        try:
            data = json.loads(request.body)
            notification_id = data.get("id")
        except (json.JSONDecodeError, KeyError):
            return JsonResponse(
                {"success": False, "error": "Invalid JSON data"}, status=400
            )
    else:
        notification_id = request.POST.get("notification_id")

    if not notification_id:
        return JsonResponse(
            {"success": False, "error": "Missing notification ID"}, status=400
        )

    try:
        notification = get_object_or_404(
            Notification, id=notification_id, user=request.user
        )
        notification.is_read = True
        notification.save()

        # Get updated unread count
        unread_count = Notification.objects.filter(
            user=request.user, is_read=False
        ).count()

        return JsonResponse(
            {
                "success": True,
                "unread_count": unread_count,
                "message": "Notification marked as read",
            }
        )
    except Notification.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Notification not found"}, status=404
        )


@login_required
@require_POST
def mark_as_read(request):
    """New endpoint specifically for JSON requests to mark notifications as read."""
    import json

    try:
        data = json.loads(request.body)
        notification_id = data.get("id")
        redirect_url = data.get("redirect_url", "/notifications/")
    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "error": "Invalid JSON data"}, status=400
        )

    if not notification_id:
        return JsonResponse(
            {"success": False, "error": "Missing notification ID"}, status=400
        )

    try:
        notification = Notification.objects.get(id=notification_id, user=request.user)
        notification.is_read = True
        notification.save()

        # Get updated unread count
        unread_count = Notification.objects.filter(
            user=request.user, is_read=False
        ).count()

        return JsonResponse(
            {
                "success": True,
                "unread_count": unread_count,
                "redirect_url": redirect_url,
                "message": "Notification marked as read",
            }
        )
    except Notification.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Notification not found"}, status=404
        )
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
@require_POST
def mark_all_notifications_read(request):
    updated_count = Notification.objects.filter(
        user=request.user, is_read=False
    ).update(is_read=True)
    return JsonResponse(
        {
            "success": True,
            "unread_count": 0,  # All are now read
            "marked_count": updated_count,
        }
    )


@login_required
@require_POST
def delete_notification(request, notification_id):
    notification = get_object_or_404(
        Notification, id=notification_id, user=request.user
    )
    notification.delete()
    return JsonResponse({"success": True})


@login_required
@require_POST
def clear_all_notifications(request):
    Notification.objects.filter(user=request.user).delete()
    return JsonResponse({"success": True})


@login_required
def handle_legacy_mark_read(request, notification_id):
    """Handle legacy mark_notification_as_read URLs, especially those with 'undefined' IDs."""
    if notification_id == "undefined" or not notification_id:
        return JsonResponse(
            {
                "success": False,
                "error": "Invalid notification ID",
                "message": "Cannot mark notification as read: ID is undefined",
            },
            status=400,
        )

    try:
        notification_id = int(notification_id)
    except (ValueError, TypeError):
        return JsonResponse(
            {
                "success": False,
                "error": "Invalid notification ID format",
                "message": "Notification ID must be a valid number",
            },
            status=400,
        )

    if request.method == "POST":
        try:
            notification = get_object_or_404(
                Notification, id=notification_id, user=request.user
            )
            notification.is_read = True
            notification.save()

            # Get updated unread count
            unread_count = Notification.objects.filter(
                user=request.user, is_read=False
            ).count()

            return JsonResponse(
                {
                    "success": True,
                    "unread_count": unread_count,
                    "message": "Notification marked as read",
                }
            )
        except Notification.DoesNotExist:
            return JsonResponse(
                {"success": False, "error": "Notification not found"}, status=404
            )
    else:
        # Handle GET requests by redirecting to notifications page
        from django.shortcuts import redirect

        return redirect("notifications:notifications_page")
