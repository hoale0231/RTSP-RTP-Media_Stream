import socket, threading, os
from RtpPacket import RtpPacket
from time import time
from flask import Flask, request 
from flask_socketio import SocketIO

app = Flask(__name__)
app.config['SECRET_KEY'] = 'top-secret!'
socketio = SocketIO(app, manage_session=False, cors_allowed_origins='*')

CACHE_FILE_NAME = "cache-"
CACHE_FILE_EXT = ".jpg"

class Client:
	INIT = 0
	READY = 1
	PLAYING = 2
	state = INIT
	
	SETUP = 0
	PLAY = 1
	PAUSE = 2
	TEARDOWN = 3
	
	def __init__(self, serveraddr, serverport, rtpport, filename, wio, requestSid):
		self.serverAddr = serveraddr
		self.serverPort = int(serverport)
		self.rtpPort = int(rtpport)
		self.fileName = filename
		self.rtspSeq = 0
		self.sessionId = 0
		self.requestSent = -1
		self.teardownAcked = 0
		self.frameNbr = 0
		self.playEvent = threading.Event()
		self.wio = wio
		self.requestSid = requestSid
	
	def setupMovie(self):
		"""Setup button handler."""
		if self.state == Client.INIT:
			# Reset session state
			self.rtspSeq = 0
			self.frameNbr = 0
			self.teardownAcked = 0
			# Setup RTSP
			self.connectToServer()
			threading.Thread(target=self.recvRtspReply).start()
			# Send request
			self.sendRtspRequest(Client.SETUP)
	
	def exitClient(self):
		"""Teardown button handler."""
		# Pause movie if it is playing
		if self.state == Client.PLAYING:
			self.pauseMovie()
			while self.state == Client.PLAYING:
				continue
		
		if self.state == Client.READY:
			# Send request
			self.sendRtspRequest(Client.TEARDOWN)
			if os.path.exists(CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT):
				os.remove(CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT)

	def pauseMovie(self):
		"""Pause button handler."""
		if self.state == Client.PLAYING:
			self.playEvent.set()
			self.sendRtspRequest(Client.PAUSE)
	
	def playMovie(self):
		"""Play button handler."""
		# If not yet setup connection, setup it.
		if self.state == Client.INIT:
			self.setupMovie()
			while self.state == Client.INIT:
				continue
		# Play movie
		if self.state == Client.READY:
			self.playEvent = threading.Event()
			self.playEvent.clear()
			threading.Thread(target=self.listenRtp).start()
			self.sendRtspRequest(Client.PLAY)
			
	def listenRtp(self):		
		"""Listen for RTP packets."""
		packetLoss = 0
		packetSlow = 0
		videoData = 0
		start = time()
		while True:
			try:
				data = self.rtpSocket.recv(20480)
				if data:
					rtpPacket = RtpPacket()
					rtpPacket.decode(data)
					currFrameNbr = rtpPacket.seqNum()
					# Count loss packet
					if currFrameNbr > self.frameNbr + 1:
						packetLoss += currFrameNbr - (self.frameNbr + 1) 
					# Count slow packet
					if currFrameNbr < self.frameNbr:
						packetSlow += 1
					# Update frame
					if currFrameNbr > self.frameNbr: 
						self.frameNbr = currFrameNbr
						payload = rtpPacket.getPayload()
						self.updateMovie(payload)
						# Count video data
						videoData += len(payload)
			except:
				# Stop listening if request is PAUSE or TEARDOWN
				if self.playEvent.isSet():
					break
				if self.teardownAcked:
					self.rtpSocket.shutdown(socket.SHUT_RDWR)
					self.rtpSocket.close()
					break
		end = time()
		# Calc and print data transmission parameters
		print("\n===============================")
		print(f"RTP Packet Loss Rate = {packetLoss-packetSlow}/{self.frameNbr} = {100 * (packetLoss-packetSlow)/self.frameNbr} %")
		print(f"RTP Packet Loss Rate = {packetSlow}/{self.frameNbr} = {100 * packetSlow /self.frameNbr} %")
		print(f"Video data rate = {videoData}/{end - start} = {videoData/(end - start)} bytes/sec")
		print("===============================\n")
									
	def updateMovie(self, imageFile):
		"""Update the image file as video frame in the GUI."""
		self.wio.send(imageFile, to=self.requestSid)
		
	def connectToServer(self):
		"""Connect to the Server. Start a new RTSP/TCP session."""
		self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		try:
			self.rtspSocket.connect((self.serverAddr, self.serverPort))
		except:
			print('Connect Failed!')
			#tkinter.messagebox.showwarning(f"Connect to {self.serverAddr} at port {self.serverPort} failed!")
	
	def sendRtspRequest(self, requestCode):
		"""Send RTSP request to the server."""	
		request = ""
		self.rtspSeq += 1
		if requestCode == Client.SETUP:
			request += f"SETUP {self.fileName} RTSP/1.0\n"
			request += f"CSeq: {self.rtspSeq}\n"
			request += f"Transport: RTP/UDP; client_port= {self.rtpPort}\n"
		else:
			if requestCode == Client.PLAY:
				request += "PLAY"
			if requestCode == Client.PAUSE:
				request += "PAUSE"
			if requestCode == Client.TEARDOWN:
				request += "TEARDOWN"
			request += f" {self.fileName} RTSP/1.0\n"
			request += f"CSeq: {self.rtspSeq}\n"
			request += f"Session: {self.sessionId}\n"
		self.requestSent = requestCode
		self.rtspSocket.send(request.encode())
	
	def recvRtspReply(self):
		"""Receive RTSP reply from the server."""
		while True:
			# Stop listening if teardown
			if self.teardownAcked:
				self.rtspSocket.shutdown(socket.SHUT_RDWR)
				self.rtspSocket.close()
				break
			# Recv reply and process
			data = self.rtspSocket.recv(256)
			if data: 
				self.parseRtspReply(data.decode())
				
	def parseRtspReply(self, data: str):
		"""Parse the RTSP reply from the server."""
		response = data.split('\n')
		code = int(response[0].split(' ')[1])
		# Check status code
		if code == 200:
			seq = int(response[1].split(' ')[1])
			# Check sequence number
			if seq == self.rtspSeq:
				session = int(response[2].split(' ')[1])
				# If requestSend is SETUP, update session ID
				if self.requestSent == Client.SETUP:
					self.sessionId = session
					self.state = Client.READY
					self.openRtpPort()
				else:
					# Else check session ID and process the reply
					if self.sessionId != session: return
					if self.requestSent == Client.PLAY:
						self.state = Client.PLAYING
					elif self.requestSent == Client.PAUSE:
						self.state = Client.READY
					elif self.requestSent == Client.TEARDOWN:
						self.state = Client.INIT
						self.teardownAcked = 1
		elif code == 404:
			#tkinter.messagebox.showwarning('File not found!')
			print('File not found')
		elif code == 500:
			print('Connection error')
			#tkinter.messagebox.showwarning('Connection error!')
		
	def openRtpPort(self):
		"""Open RTP socket binded to a specified port."""
		# Create a new datagram socket to receive RTP packets from the server
		self.rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		# Set the timeout value of the socket to 0.5sec
		self.rtpSocket.settimeout(0.5)
		try:
			self.rtpSocket.bind(('', self.rtpPort))
		except:
			print(f"Bind tp port {self.rtpPort} faild!")
			#tkinter.messagebox.showwarning(f"Bind tp port {self.rtpPort} faild!")

clients = {}
clientPort = 1026
SERVER_PORT = 1025

@socketio.on('connect')
def addClient():
	global clientPort
	print("REQUEST SID", request.sid)
	clients[request.sid] = Client('localhost', SERVER_PORT, clientPort, 'movie.Mjpeg', socketio,request.sid)
	clientPort += 1


@socketio.on('message')
def handleMessage(msg):
	print('Message: ' + msg)
	print("REQUEST SID", request.sid)
	if msg == 'PLAY':
		clients[request.sid].playMovie()
	elif msg == 'PAUSE':
		clients[request.sid].pauseMovie()
	elif msg == 'STOP':
		clients[request.sid].exitClient()
		
if __name__ == '__main__':
    socketio.run(app)