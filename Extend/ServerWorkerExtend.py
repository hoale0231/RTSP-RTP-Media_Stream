from random import randint
from Normal.ServerWorker import ServerWorker
from glob import glob
import socket
import threading
from Normal.VideoStream import VideoStream

class ServerWorkerExtend(ServerWorker):
	SWITCH = 3

	GETLIST = 'GETLIST'
	SETTIME = 'SETTIME'
	CONNECT = 'CONNECT'
	CHANGE = 'CHANGE'
	DESCRIBE = 'DESCRIBE'

	def processRtspRequest(self, data: str):
		"""Process RTSP request sent from the client."""
		# Get the request type
		request = data.split('\n')
		line1 = request[0].split(' ')
		requestType = line1[0]
		
		# Get the RTSP sequence number 
		seq = request[1].split(' ')
		
		# Process CONNECT request
		if requestType == self.CONNECT:
			if self.state == self.INIT:
				# Update state
				print("processing CONNECT\n")
				self.state = self.SWITCH

				# Generate a randomized RTSP session ID
				self.clientInfo['session'] = randint(100000, 999999)
				
				# Send RTSP reply
				self.replyRtsp(self.OK_200, seq[1])
				
				# Get the RTP/UDP port from the last line
				self.clientInfo['rtpPort'] = request[2].split(' ')[3]
			return
		
		# Get the media file name
		filename = line1[1]
		
		# Process SETUP request 		
		if requestType == self.SETUP:
			if self.state == self.SWITCH:
				print("processing SETUP\n")
				try:
					self.clientInfo['videoStream'] = VideoStream('video/'+filename)
					# Update state
					self.state = self.READY
				except IOError:
					self.replyRtsp(self.FILE_NOT_FOUND_404, seq[1])
				# Send RTSP reply
				self.replyRtsp(self.OK_200, seq[1])
				
		# Process PLAY request 		
		if requestType == self.PLAY:
			if self.state == self.READY:
				print("processing PLAY\n")
				# Update state
				self.state = self.PLAYING
				# Create a new socket for RTP/UDP
				self.clientInfo["rtpSocket"] = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
				# Send RSTP reply
				self.replyRtsp(self.OK_200, seq[1], self.PLAY)
				# Create a new thread and start sending RTP packets
				self.clientInfo['event'] = threading.Event()
				self.clientInfo['worker']= threading.Thread(target=self.sendRtp) 
				self.clientInfo['worker'].start()
		
		# Process PAUSE request
		elif requestType == self.PAUSE:
			if self.state == self.PLAYING:
				print("processing PAUSE\n")
				# Update state
				self.state = self.READY
				# Pause sending video frame
				self.clientInfo['event'].set()
				# Send RSTP reply
				self.replyRtsp(self.OK_200, seq[1])
		
		# Process TEARDOWN request
		elif requestType == self.TEARDOWN:
			if self.state != self.INIT:
				print("processing TEARDOWN\n")
				# Stop sending video frame
				self.clientInfo['event'].set()
				# Send RSTP reply
				self.replyRtsp(self.OK_200, seq[1])
				# Close the RTP socket
				self.clientInfo['rtpSocket'].close()
				
		# Process GETLIST request
		elif requestType == self.GETLIST:
			print("processing GETLIST")
			# Send List video
			self.sendListVideo(seq[1])

		# Process SETTIME request
		elif requestType == self.SETTIME:
			print("processing SETTIME")
			# Update frame number
			newFrameNbr = int(request[3].split(' ')[1])
			self.clientInfo['videoStream'].setFrameNbr(newFrameNbr)
			# Send reply request
			self.replyRtsp(self.OK_200, seq[1])
		
		# Process CHANGE request
		elif requestType == self.CHANGE:
			if self.state == self.READY or self.state == self.SWITCH:
				print("processing CHANGE")
				# Check if video exists
				try:
					self.clientInfo['videoStream'] = VideoStream('video/'+filename)
					self.state = self.SWITCH
				except IOError:
					self.replyRtsp(self.FILE_NOT_FOUND_404, seq[1])
				# Send RTSP reply
				self.replyRtsp(self.OK_200, seq[1])

		elif requestType == self.DESCRIBE:
			print("processing DESCRIBE")
			if self.state != self.SWITCH:
				# Send RTSP reply
				self.replyRtsp(self.OK_200, seq[1], self.DESCRIBE)

	def replyRtsp(self, code, seq, type = ""):
		"""Send RTSP reply to the client."""
		if code == self.OK_200:
			#print("200 OK")
			reply = 'RTSP/1.0 200 OK\nCSeq: ' + seq + '\nSession: ' + str(self.clientInfo['session'])
			if type == self.PLAY:
				reply += f"\nTTtime: {int(self.clientInfo['videoStream'].totalTime())}"
			if type == self.DESCRIBE:
				reply += f"\n\nstream=video\n"
				reply += f"type=Mjpeg\n"
				reply += f"NumFrame={int(self.clientInfo['videoStream'].totalTime()*20)}\n"
				reply += f"protocol=RTP\n"
				reply += f"version=2\n"
			connSocket = self.clientInfo['rtspSocket'][0]
			connSocket.send(reply.encode())
		
		# Error messages
		elif code == self.FILE_NOT_FOUND_404:
			print("404 NOT FOUND")
		elif code == self.CON_ERR_500:
			print("500 CONNECTION ERROR")

	def sendListVideo(self, seq):
		reply = f"RTSP/1.0 200 OK\n"
		reply += f"CSeq: {seq}\n"
		reply += f"Session: {self.clientInfo['session']}\n"
		listVideo = [video.split('\\')[1] for video in glob("video/*.Mjpeg")]
		reply += f"NVideo: {len(listVideo)}\n"
		for video in listVideo:
			reply += video + '\n'
		reply = reply[:-1]
		connSocket: socket.socket = self.clientInfo['rtspSocket'][0]
		connSocket.send(reply.encode())
