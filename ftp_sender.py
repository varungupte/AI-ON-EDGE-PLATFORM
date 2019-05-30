import socket
import sys


filename = sys.argv[1]
f=sys.argv[1].split('/')[-1]

fp = open(filename, "rb")
read_data = fp.read()
print ("Sending",filename)
ip = sys.argv[2]
app_name=sys.argv[3]
port = 8083
print ("IP",ip)
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
print("Connecting to: "+ip+":"+str(port))
s.connect((ip, port))
s.send(f)
s.recv(1024)
s.send(app_name)
s.recv(1024)

s.sendall(read_data)
s.close()
