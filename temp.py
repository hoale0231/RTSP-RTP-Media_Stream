import random
class VideoStream:
	def __init__(self, filename):
		self.data = []
		self.head = []
		try:
			file = open(filename, 'rb')
			cfile = open('video/meovi.Mjpeg', 'wb')
			while True:
				data = file.read(5)
				if data:
					framelength = int(data)
					self.data.append(file.read(framelength))
					self.head.append(data)
				else:
					break
			a = [i for i in range(len(self.data))]
			random.shuffle(a) 
			for i in a:
				cfile.write(self.head[i])
				cfile.write(self.data[i])

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

VideoStream('video/movie.Mjpeg')

