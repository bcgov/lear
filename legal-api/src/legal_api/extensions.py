from flask import current_app
from flask_socketio import SocketIO

socketio = SocketIO()


@socketio.on('connect')
def on_connect():
    current_app.logger.debug(f"Socket connected to client")
