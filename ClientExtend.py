from tkinter import *
import tkinter.messagebox
from PIL import Image, ImageTk
import socket, threading,  os
from RtpPacket import RtpPacket
from Client import Client

CACHE_FILE_NAME = "cache-"
CACHE_FILE_EXT = ".jpg"

class ClientExtend(Client):
	SWITCH = 3
	
	GETLIST = 4
	SETTIME = 5
	CHECK = 6
	CHANGE = 7

	def __init__(self, master, serveraddr, serverport, rtpport, filename):
		super().__init__(master, serveraddr, serverport, rtpport, filename)
		self.totalFrame = 0

	def createWidgets(self):
		"""Build GUI."""
		# Create a label to display the movie
		self.label = Label(self.master, height=19)
		self.label.grid(row=0, column=0, columnspan=5, rowspan=2,sticky=W+E+N+S, padx=5, pady=5) 
	
		# Create Play button		
		self.start = Button(self.master, width=15, padx=3, pady=3)
		self.start["text"] = "Play"
		self.start["command"] = self.playMovie
		self.start.grid(row=3, column=1, padx=2, pady=2)
		
		# Create Pause button			
		self.pause = Button(self.master, width=15, padx=3, pady=3)
		self.pause["text"] = "Pause"
		self.pause["command"] = self.pauseMovie
		self.pause.grid(row=3, column=2, padx=2, pady=2)
		
		# Create Teardown button
		self.stop_reload = Button(self.master, width=15, padx=3, pady=3)
		self.stop_reload["text"] = "STOP"
		self.stop_reload["command"] =  self.exitClient
		self.stop_reload.grid(row=3, column=3, padx=2, pady=2)

		# Create Forward video button
		self.forward = Button(self.master, width=5, padx=3, pady=3)
		self.forward["text"] = ">>"
		self.forward["command"] = self.forwardVideo
		self.forward.grid(row=3, column=4)

		# Create Backward video button
		self.backward = Button(self.master, width=5)
		self.backward["text"] = "<<"
		self.backward["command"] = self.backwardVideo
		self.backward.grid(row=3, column=0, padx=2, pady=2)

		# Create Get list button
		self.switch = Button(self.master, width=15, height=1, padx=3, pady=3)
		self.switch["text"] = "Get List Video"
		self.switch["command"] =  self.getListVideo
		self.switch.grid(row=0, column=5, padx=2, pady=2, sticky=N)

		# Create list video label
		self.songsFrame = LabelFrame(self.master, text='List Video', height=30)
		self.songsFrame.grid(row=0, column=5, sticky=S)
		self.scrol_y = Scrollbar(self.songsFrame, orient=VERTICAL)
		self.listVideo = Listbox(self.songsFrame, yscrollcommand=self.scrol_y.set)
		self.listVideo.grid(row=0, column=5, sticky=N)

		self.listVideo.bind('<Double-1>', self.switchVideo)

		# Create time scroll bar	
		self.scroll = Scale(self.master, from_=0, to=100, orient=HORIZONTAL, command=self.settime)
		self.scroll.grid(row=2, column=1, columnspan=3, sticky=W+E+N+S)

		# Create total time label
		self.totalTime = Label(self.master)
		self.totalTime["text"] = "00"
		self.totalTime.grid(row=2, column=4 , sticky=W+S)

	def forwardVideo(self):
		"""Forward video button handler."""
		if self.state != self.PLAYING and self.state != self.READY:
			return
		self.frameNbr += 20 * 5 # 5 second
		if self.frameNbr > self.totalFrame:
			self.frameNbr = self.totalFrame
		self.sendRtspRequest(ClientExtend.SETTIME)

	def backwardVideo(self):
		"""Backward video button handler."""
		if self.state != self.PLAYING and self.state != self.READY:
			return
		self.frameNbr -= 20 * 5 # 5 second
		if self.frameNbr < 0: self.frameNbr = 0
		self.sendRtspRequest(self.SETTIME)

	def settime(self, value):
		value = int(value)
		if self.frameNbr > value * 20 + 10 or self.frameNbr < value * 20 - 10:
			print(value)
			self.frameNbr = int(value) * 20
			self.sendRtspRequest(self.SETTIME)

	def getListVideo(self):
		self.listVideo.delete(0, END)
		self.sendRtspRequest(ClientExtend.GETLIST)

	def playMovie(self):
		"""Play button handler."""
		if self.state == ClientExtend.INIT:
			self.setupMovie()
			while self.state == Client.INIT:
				continue
		if self.state == ClientExtend.SWITCH:
			self.sendRtspRequest(ClientExtend.CHANGE)
			while self.state == ClientExtend.SWITCH:
				continue
		if self.state == ClientExtend.READY:
			self.playEvent = threading.Event()
			self.playEvent.clear()
			threading.Thread(target=self.listenRtp).start()
			self.sendRtspRequest(ClientExtend.PLAY)

	def switchVideo(self, value):
		if self.state == ClientExtend.PLAYING:
			self.pauseMovie()
			while self.state == Client.PLAYING:
				continue
		if self.state == ClientExtend.READY:
			self.fileName = self.listVideo.get(ACTIVE)
			self.sendRtspRequest(ClientExtend.CHECK)

	def updateMovie(self, imageFile):
		"""Update the image file as video frame in the GUI."""
		photo = ImageTk.PhotoImage(Image.open(imageFile)) 
		self.label.configure(image = photo, height=288)
		self.label.image = photo
		self.scroll.set(self.frameNbr//20)

	def sendRtspRequest(self, requestCode):
			"""Send RTSP request to the server."""	
			request = ""
			if requestCode == ClientExtend.SETUP:
				self.rtspSeq = 1
				request += f"SETUP {self.fileName} RTSP/1.0\n"
				request += f"CSeq: {self.rtspSeq}\n"
				request += f"Transport: RTP/UDP; client_port= {self.rtpPort}\n"
			else:
				if requestCode == ClientExtend.PLAY:
					request += f"PLAY {self.fileName}"
				if requestCode == ClientExtend.PAUSE:
					request += f"PAUSE {self.fileName}"
				if requestCode == ClientExtend.TEARDOWN:
					request += f"TEARDOWN {self.fileName}"
				if requestCode == ClientExtend.GETLIST:
					request += f"GETLIST "
				if requestCode == ClientExtend.SETTIME:
					request += f"SETTIME {self.fileName} {self.frameNbr}"
				if requestCode == ClientExtend.CHECK:
					request += f"CHECK {self.fileName}"
				if requestCode == ClientExtend.CHANGE:
					request += f"CHANGE {self.fileName}"
				request += f" RTSP/1.0\n"
				request += f"CSeq: {self.rtspSeq}\n"
				request += f"Session: {self.sessionId}\n"
			self.requestSent = requestCode
			self.rtspSocket.send(request.encode())

	def parseRtspReply(self, data: str):
		"""Parse the RTSP reply from the server."""
		print(self.requestSent, data)
		response = data.split('\n')
		code = int(response[0].split(' ')[1])
		
		if code == 200:
			seq = int(response[1].split(' ')[1])
			if seq == self.rtspSeq:
				session = int(response[2].split(' ')[1])
				if self.requestSent == ClientExtend.SETUP:
					self.sessionId = session
					self.state = ClientExtend.READY
					self.openRtpPort()
				else:
					if self.sessionId != session: return
					if self.requestSent == ClientExtend.PLAY:
						self.setTimeVideo(int(response[3].split(' ')[1]))
						self.state = ClientExtend.PLAYING
					elif self.requestSent == ClientExtend.PAUSE:
						self.state = ClientExtend.READY
					elif self.requestSent == ClientExtend.TEARDOWN:
						self.state = ClientExtend.INIT
						self.teardownAcked = 1
					elif self.requestSent == ClientExtend.GETLIST:
						for video in response[4:]:
							self.listVideo.insert(END, video)
					elif self.requestSent == ClientExtend.SETTIME:
						pass
					elif self.requestSent == ClientExtend.CHECK:
						self.state = ClientExtend.SWITCH
						self.start['text'] = 'Reload'
						self.frameNbr = 0
					elif self.requestSent == ClientExtend.CHANGE:
						self.state = ClientExtend.READY
						self.start['text'] = 'Play'

		elif code == 404:
			tkinter.messagebox.showwarning('File not found!')
		elif code == 500: 
			tkinter.messagebox.showwarning('Connection error!')
		
	def setTimeVideo(self, time):
		self.totalTime["text"] = f"{time/20}"
		self.scroll["to"] = time/20
		self.totalFrame = time