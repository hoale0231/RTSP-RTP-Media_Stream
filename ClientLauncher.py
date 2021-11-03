import sys
from tkinter import Tk
from Normal.Client import Client
from Extend.Client3Button import Client3Button
from Extend.ClientExtend import ClientExtend

if __name__ == "__main__":
	try:
		serverAddr = sys.argv[1]
		serverPort = sys.argv[2]
		rtpPort = sys.argv[3]
		fileName = sys.argv[4]
		mode = 0 if len(sys.argv) == 5 else int(sys.argv[5])
	except:
		print("[Usage: ClientLauncher.py Server_name Server_port RTP_port Video_file mode]\n")	
	
	root = Tk()
	
	client = Client if (mode == 0) else (Client3Button if (mode == 1) else ClientExtend)
	# Create a new client
	app = client(root, serverAddr, serverPort, rtpPort, fileName)
	app.master.title("RTPClient")	
	root.mainloop()
	