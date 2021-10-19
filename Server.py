import sys, socket

from ServerWorker import ServerWorker
from ServerWorkerExtend import ServerWorkerExtend
class Server:	
	
	def main(self):
		try:
			SERVER_PORT = int(sys.argv[1])
			mode = 0 if len(sys.argv) == 2 else int(sys.argv[2])
		except:
			print("[Usage: Server.py Server_port]\n")
		rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		rtspSocket.bind(('', SERVER_PORT))
		rtspSocket.listen(5)        

		# Receive client info (address,port) through RTSP/TCP session
		while True:
			clientInfo = {}
			clientInfo['rtspSocket'] = rtspSocket.accept()
			if mode == 0:
				ServerWorker(clientInfo).run()
			else:
				ServerWorkerExtend(clientInfo).run()

if __name__ == "__main__":
	(Server()).main()


