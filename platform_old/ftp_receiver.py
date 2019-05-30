from threading import Thread
import socket
import sys
import zipfile


class ListenClientMaster(Thread):
    def __init__(self,sock, self_ip, self_port):
    	Thread.__init__(self)
    	self.sock = sock
    	self.ip = self_ip
    	self.port = self_port

    def run(self):
    	data = []
    	filename = self.sock.recv(1024)
    	print(filename)
    	self.sock.send("ok")
        app_name = self.sock.recv(1024)
        print(app_name)
        self.sock.send("ok")


    	RCVCHUNKSIZE = 1024*1024*64
    	total_len = RCVCHUNKSIZE
    	while total_len:
    		data_rcv = self.sock.recv(RCVCHUNKSIZE)
    		if not data_rcv:
    			break
    		data.append(data_rcv)
    		total_len = total_len-len(data_rcv)
    	data = b''.join(data)
    	f = open(app_name+"/"+filename,'wb')
    	f.write(data)
    	f.close()
        zip_ref = zipfile.ZipFile(app_name+"/"+filename, 'r')
        zip_ref.extractall(app_name)
        zip_ref.close()

		

self_ip = sys.argv[1]
self_port = '8083'
    
tcpsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
tcpsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
tcpsock.bind((self_ip, int(self_port)))

while True:
	tcpsock.listen(1000)
	print ("Waiting for incoming connections...")
	(conn, (ip,port)) = tcpsock.accept()
	listenthread = ListenClientMaster(conn, self_ip, self_port)
	listenthread.daemon = True
	listenthread.start()
