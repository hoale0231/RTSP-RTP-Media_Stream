class VideoStream:
	def __init__(self, filename):
		self.data = []
		try:
			file = open(filename, 'rb')
			while True:
				data = file.read(5)
				if data:
					framelength = int(data)
					self.data.append(file.read(framelength))
				else:
					break
		except:
			raise IOError
		self.frameNum = 0
		
		
	def nextFrame(self):
		"""Get next frame."""	
		#data = self.file.read(5) # Get the framelength from the first 5 bits
		if self.frameNum < len(self.data): 
			# framelength = int(data)
							
			# # Read the current frame
			data = self.data[self.frameNum]
			self.frameNum += 1
			return data
		
	def frameNbr(self):
		"""Get frame number."""
		return self.frameNum

	def totalTime(self):
		return len(self.data)

	def setFrameNbr(self, num):
		self.frameNum = num
	