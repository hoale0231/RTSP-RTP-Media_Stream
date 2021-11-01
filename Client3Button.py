from tkinter import *
import threading
from Client import Client

class Client3Button(Client):

	def createWidgets(self):
		"""Build GUI."""

		# Create Play button		
		self.start = Button(self.master, width=20, padx=3, pady=3)
		self.start["text"] = "Play"
		self.start["command"] = self.playMovie
		self.start.grid(row=1, column=0, padx=2, pady=2)
		
		# Create Pause button			
		self.pause = Button(self.master, width=20, padx=3, pady=3)
		self.pause["text"] = "Pause"
		self.pause["command"] = self.pauseMovie
		self.pause.grid(row=1, column=1, padx=2, pady=2)
		
		# Create STOP button
		self.teardown = Button(self.master, width=20, padx=3, pady=3)
		self.teardown["text"] = "STOP"
		self.teardown["command"] =  self.exitClient
		self.teardown.grid(row=1, column=2, padx=2, pady=2)
		
		# Create a label to display the movie
		self.label = Label(self.master, height=19)
		self.label.grid(row=0, column=0, columnspan=3, sticky=W+E+N+S, padx=5, pady=5) 
	
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