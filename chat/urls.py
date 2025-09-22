from django.urls import path
from . import views

app_name = "chat"

urlpatterns = [
    path("chatrooms/", views.chatroom_list, name="chatroom_list"),
    path("room/<int:room_id>/", views.chatroom, name="chatroom"),
    path("room/project/<int:project_id>/", views.chatroom, name="chatroom_by_project"),
    path(
        "room/<int:chatroom_id>/milestone/create/",
        views.create_milestone,
        name="create_milestone",
    ),
    path(
        "milestone/<int:milestone_id>/complete/",
        views.complete_milestone,
        name="complete_milestone",
    ),
    path("message/<int:mess_age_id>/pin/", views.pin_message, name="pin_message"),
    path(
        "room/<int:chatroom_id>/status/change/",
        views.handle_project_status_change,
        name="change_status",
    ),
]
