from tkinter import *
import tkinter.messagebox
from PIL import Image, ImageTk
import socket, threading, os
from RtpPacket import RtpPacket
import glob
from time import time

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
	
	def __init__(self, master, serveraddr, serverport, rtpport, filename):
		self.master = master
		self.master.protocol("WM_DELETE_WINDOW", self.handler)
		self.createWidgets()
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

	# Initiatio
	# THIS GUI IS JUST FOR REFERENCE ONLY, STUDENTS HAVE TO CREATE THEIR OWN GUI 	
	def createWidgets(self):
		"""Build GUI."""
		# Create Setup button
		self.setup = Button(self.master, width=20, padx=3, pady=3)
		self.setup["text"] = "Setup"
		self.setup["command"] = self.setupMovie
		self.setup.grid(row=1, column=0, padx=2, pady=2)
		
		# Create Play button		
		self.start = Button(self.master, width=20, padx=3, pady=3)
		self.start["text"] = "Play"
		self.start["command"] = self.playMovie
		self.start.grid(row=1, column=1, padx=2, pady=2)
		
		# Create Pause button			
		self.pause = Button(self.master, width=20, padx=3, pady=3)
		self.pause["text"] = "Pause"
		self.pause["command"] = self.pauseMovie
		self.pause.grid(row=1, column=2, padx=2, pady=2)
		
		# Create Teardown button
		self.teardown = Button(self.master, width=20, padx=3, pady=3)
		self.teardown["text"] = "Teardown"
		self.teardown["command"] =  self.exitClient
		self.teardown.grid(row=1, column=3, padx=2, pady=2)
		
		# Create a label to display the movie
		self.label = Label(self.master, height=19)
		self.label.grid(row=0, column=0, columnspan=4, sticky=W+E+N+S, padx=5, pady=5) 
	
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
		if self.state == Client.READY:
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
						self.updateMovie(self.writeFrame(payload))
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
								
	def writeFrame(self, data):
		"""Write the received frame to a temp image file. Return the image file."""
		cachename = CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT
		file = open(cachename, "wb")
		file.write(data)
		file.close()
		return cachename
	
	def updateMovie(self, imageFile):
		"""Update the image file as video frame in the GUI."""
		photo = ImageTk.PhotoImage(Image.open(imageFile)) 
		self.label.configure(image = photo, height=288)
		self.label.image = photo
		
	def connectToServer(self):
		"""Connect to the Server. Start a new RTSP/TCP session."""
		self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		try:
			self.rtspSocket.connect((self.serverAddr, self.serverPort))
		except:
			tkinter.messagebox.showwarning(f"Connect to {self.serverAddr} at port {self.serverPort} failed!")
	
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
			tkinter.messagebox.showwarning('File not found!')
		elif code == 500: 
			tkinter.messagebox.showwarning('Connection error!')
		
	def openRtpPort(self):
		"""Open RTP socket binded to a specified port."""
		# Create a new datagram socket to receive RTP packets from the server
		self.rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		# Set the timeout value of the socket to 0.5sec
		self.rtpSocket.settimeout(0.5)
		try:
			self.rtpSocket.bind(('', self.rtpPort))
		except:
			tkinter.messagebox.showwarning(f"Bind tp port {self.rtpPort} faild!")

	def handler(self):
		"""Handler on explicitly closing the GUI window."""
		# Pause Movie if it is playing
		self.pauseMovie()
		# Ask user again
		if tkinter.messagebox.askokcancel("Quit?", "Are you sure you want to quit?"):
			# Remove all cache file
			for file in glob.iglob(CACHE_FILE_NAME+'*'+CACHE_FILE_EXT):
				os.remove(file)
			# Teardown session
			self.exitClient()
			# Close app
			self.master.destroy()
		else: 
			# When the user presses cancel, resume playing.
			self.playMovie()