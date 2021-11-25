from random import randint
import threading
from Normal.VideoStream import VideoStream

class ServerWorker:
	SETUP = 'SETUP'
	PLAY = 'PLAY'
	PAUSE = 'PAUSE'
	TEARDOWN = 'TEARDOWN'
	SETTIME = 'SETTIME'

	INIT = 0
	READY = 1
	PLAYING = 2
	state = INIT

	OK_200 = 0
	FILE_NOT_FOUND_404 = 1
	CON_ERR_500 = 2
	
	clientInfo = {}
	
	def __init__(self, clientInfo):
		self.clientInfo = clientInfo
		self.clientInfo['event'] = threading.Event()
	
	def processRtspRequest(self, data):
		"""Process RTSP request sent from the client."""
		# Get the request type
		print(data)
		request = data.split('\n')
		line1 = request[0].split(' ')
		requestType = line1[0]
		
		# Get the media file name
		filename = line1[1]
		
		# Get the RTSP sequence number 
		seq = request[1].split(' ')
		
		# Process SETUP request
		if requestType == self.SETUP:
			if self.state == self.INIT:
				# Update state
				print("processing SETUP\n")
				try:
					self.clientInfo['videoStream'] = VideoStream('video/'+filename)
					self.state = self.READY
				except IOError:
					self.replyRtsp(self.FILE_NOT_FOUND_404, seq[1])
				
				# Generate a randomized RTSP session ID
				self.clientInfo['session'] = randint(100000, 999999)
				
				# Send RTSP reply
				self.replyRtsp(self.OK_200, seq[1])
		
		# Process PLAY request 		
		elif requestType == self.PLAY:
			if self.state == self.READY:
				print("processing PLAY\n")
				self.state = self.PLAYING
				
				self.replyRtsp(self.OK_200, seq[1], self.PLAY)
				
				# Create a new thread and start sending RTP packets
				self.clientInfo['event'] = threading.Event()
				
				self.clientInfo['worker']= threading.Thread(target=self.sendRtp) 
				self.clientInfo['worker'].start()
		
		# Process PAUSE request
		elif requestType == self.PAUSE:
			if self.state == self.PLAYING:
				print("processing PAUSE\n")
				self.state = self.READY
				
				self.clientInfo['event'].set()
			
				self.replyRtsp(self.OK_200, seq[1])
		
		# Process TEARDOWN request
		elif requestType == self.TEARDOWN:
			print("processing TEARDOWN\n")
			self.clientInfo['event'].set()
			self.clientInfo['videoStream'].setFrameNbr(0)
			self.state = self.INIT
			self.replyRtsp(self.OK_200, seq[1])
			
		# Process SETTIME request
		elif requestType == self.SETTIME:
			print("processing SETTIME\n")
			# Update frame number
			newFrameNbr = int(request[3].split(' ')[1])
			self.clientInfo['videoStream'].setFrameNbr(newFrameNbr)
			# Send reply request
			self.replyRtsp(self.OK_200, seq[1])
			
	def sendRtp(self):
		"""Send RTP packets over UDP."""
		while True:
			self.clientInfo['event'].wait(0.05) 
			
			# Stop sending if request is PAUSE or TEARDOWN
			if self.clientInfo['event'].isSet(): 
				break 
				
			data = self.clientInfo['videoStream'].nextFrame()
			if data: 
				try:
					self.clientInfo['socketIO'].emit('rtpPacket', data, to=self.clientInfo['room'])
				except Exception as e:
					print(e)
		
	def replyRtsp(self, code, seq, type=""):
		"""Send RTSP reply to the client."""
		if code == self.OK_200:
			#print("200 OK")
			reply = 'RTSP/1.0 200 OK\nCSeq: ' + seq + '\nSession: ' + str(self.clientInfo['session'])
			if type == self.PLAY:
				reply += f"\nTTtime: {int(self.clientInfo['videoStream'].totalTime())}"
			connSocket = self.clientInfo['socketIO']
			connSocket.emit('rtspRequest', reply, to=self.clientInfo['room'])

		
		# Error messages
		elif code == self.FILE_NOT_FOUND_404:
			print("404 NOT FOUND")
		elif code == self.CON_ERR_500:
			print("500 CONNECTION ERROR")
