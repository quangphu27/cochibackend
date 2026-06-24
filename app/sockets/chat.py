"""Socket.IO real-time chat events."""
from datetime import datetime
from flask import request
from flask_socketio import emit, join_room, leave_room
from flask_jwt_extended import decode_token

connected_users = {}


def register_socket_events(socketio):
    @socketio.on("connect")
    def on_connect():
        emit("connected", {"message": "Connected to Bright Future English"})

    @socketio.on("authenticate")
    def on_authenticate(data):
        try:
            token = data.get("token")
            decoded = decode_token(token)
            user_id = decoded["sub"]
            connected_users[request.sid] = user_id
            emit("authenticated", {"user_id": user_id})
        except Exception:
            emit("error", {"message": "Authentication failed"})

    @socketio.on("join_room")
    def on_join_room(data):
        room = data.get("room")
        if room:
            join_room(room)
            emit("user_joined", {"room": room, "user_id": connected_users.get(request.sid)}, room=room)

    @socketio.on("leave_room")
    def on_leave_room(data):
        room = data.get("room")
        if room:
            leave_room(room)
            emit("user_left", {"room": room}, room=room)

    @socketio.on("send_message")
    def on_send_message(data):
        user_id = connected_users.get(request.sid)
        if not user_id:
            emit("error", {"message": "Please authenticate first"})
            return
        room = data.get("room")
        message = {
            "user_id": user_id,
            "content": data.get("content"),
            "room": room,
            "timestamp": datetime.utcnow().isoformat(),
        }
        emit("new_message", message, room=room)

    @socketio.on("disconnect")
    def on_disconnect():
        connected_users.pop(request.sid, None)
