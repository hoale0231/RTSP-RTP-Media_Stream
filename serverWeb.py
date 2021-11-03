import logging
from ServerWorkerWeb import ServerWorker
from flask import Flask, request, render_template
from flask_socketio import SocketIO
from glob import glob

app = Flask(__name__)
app.config['SECRET_KEY'] = 'top-secret!'
socketio = SocketIO(app, manage_session=False, cors_allowed_origins='*', logger=False)
logging.getLogger('werkzeug').setLevel(logging.ERROR)

clients = {}

@socketio.on('connect')
def addClient():
	global clientPort
	clientInfo = {}
	clientInfo['socketIO'] = socketio
	clientInfo['room'] = request.sid
	clients[request.sid] = ServerWorker(clientInfo)
	listVideo = [video.split('\\')[1] for video in glob("video/*.Mjpeg")]
	socketio.emit('listVideo', listVideo)

@socketio.on('rtspRequest')
def handleMessage(msg):
	clients[request.sid].processRtspRequest(msg)

@socketio.on('disconnect')
def handleDisconnect():
	clients.pop(request.sid)

@app.route("/")
def hello():
    message = "Hello, World"
    return render_template('index.html', message=message)

if __name__ == "__main__":
	socketio.run(app, host='localhost')