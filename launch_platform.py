import os
import time
import xmltodict


os.system("sh /home/mypc/Desktop/final_demo/nfs_server.sh ")
time.sleep(2)
config_file=open("/home/mypc/nfs/platform/platform_configs/platform_components.xml","r")
data=config_file.read()
config_file.close()

data=xmltodict.parse(data)



lb_ip=data['platform']['loadBalancer']['ip']
lb_password=data['platform']['loadBalancer']['password']
lb_uname=data['platform']['loadBalancer']['uname']

s_ip=data['platform']['scheduler']['ip']
s_password=data['platform']['scheduler']['password']
s_uname=data['platform']['scheduler']['uname']

m_ip=data['platform']['monitor']['ip']
m_password=data['platform']['monitor']['password']
m_uname=data['platform']['monitor']['uname']

nfs_queue=[]

# print ("Deploying LoadBalancer on ",lb_uname,"'s Machine")
# os.system("sshpass -p "+lb_password+" ssh "+lb_uname+"@"+lb_ip+" 'mkdir -p platform'")
# os.system("sshpass -p "+lb_password+" scp -o StrictHostKeyChecking=no platform/loadBalancer.py "+lb_uname+"@"+lb_ip+":platform/loadBalancer.py")
os.system("sshpass -p "+lb_password+" scp -o StrictHostKeyChecking=no ~/nfs/platform/nfs_client_new.sh "+lb_uname+"@"+lb_ip+":nfs_client_new.sh")
os.system("sshpass -p "+s_password+" scp -o StrictHostKeyChecking=no ~/nfs/platform/nfs_client_new.sh "+s_uname+"@"+s_ip+":nfs_client_new.sh")
os.system("sshpass -p "+m_password+" scp -o StrictHostKeyChecking=no ~/nfs/platform/nfs_client_new.sh "+m_uname+"@"+m_ip+":nfs_client_new.sh")

if(lb_ip not in nfs_queue):		
	print ("Activating NFS on",lb_ip,lb_uname)
	# os.system("sshpass -p "+lb_password+" ssh  "+lb_uname+"@"+lb_ip+" 'nohup sh ~/nfs_client_new.sh "+lb_password+" &> nfs_logs'")
	nfs_queue.append(lb_ip)
	time.sleep(3)
print ("Starting Load Balancer")
os.system("sshpass -p "+lb_password+" ssh "+lb_uname+"@"+lb_ip+" 'nohup python3 ~/nfs/platform/loadBalancer.py 2> loadBalancer_error_logs > llogs' & ")
print ("Load Balancer Started !")

##########################################

# print ("Deploying Scheduler on ",s_uname,"'s Machine")
# os.system("sshpass -p "+s_password+" ssh "+s_uname+"@"+s_ip+" 'mkdir -p platform'")
# os.system("sshpass -p "+s_password+" scp -o StrictHostKeyChecking=no platform/scheduler.py "+s_uname+"@"+s_ip+":platform/scheduler.py")
if(s_ip not in nfs_queue):		
	print ("Activating NFS on",s_ip,s_uname)	
	os.system("sshpass -p "+s_password+" ssh  "+s_uname+"@"+s_ip+" 'nohup sh ~/nfs_client_new.sh "+s_password+" &> nfs_logs'")
	nfs_queue.append(s_ip)
	time.sleep(3)
print ("Starting Scheduler")
os.system("sshpass -p "+s_password+" ssh "+s_uname+"@"+s_ip+" 'nohup python3 ~/nfs/platform/scheduler.py 2> scheduler_error_logs > slogs' &")
print ("Scheduler Started !")

##########################################

# print ("Deploying Monitor on ",m_uname,"'s Machine")	
# os.system("sshpass -p "+m_password+" ssh "+m_uname+"@"+m_ip+" 'mkdir -p platform'")
# os.system("sshpass -p "+m_password+" scp -o StrictHostKeyChecking=no platform/monitor.py "+m_uname+"@"+m_ip+":platform/monitor.py")
if(m_ip not in nfs_queue):		
	print ("Activating NFS on",m_ip,m_uname)	
	os.system("sshpass -p "+m_password+" ssh  "+m_uname+"@"+lb_ip+" 'nohup sh ~/nfs_client_new.sh "+m_password+" &> nfs_logs'")
	nfs_queue.append(m_ip)
	time.sleep(3)
print ("Starting Monitor")
os.system("sshpass -p "+m_password+" ssh "+m_uname+"@"+m_ip+" 'nohup python3 ~/nfs/platform/monitoring.py 2> monitor_error_logs > mlogs' & ")
print ("Monitor Started !")

###############################################################################


print ("Setting Up Servers")
config_file=open("/home/mypc/nfs/platform/platform_configs/platform_servers.xml","r")
data=config_file.read()
config_file.close()

data=xmltodict.parse(data)

print (type(data['platform_servers']['server']))


for i in data['platform_servers']['server']:
	
	passw=i['password']
	uname=i['uname']
	ip=i['ip']
	print (uname,"'s Machine")
	
	# os.system("sshpass -p "+passw+" ssh "+uname+"@"+ip+" 'mkdir -p platform'")
	# print ("Sending FTP, NFS and Server Codes")
	# os.system("sshpass -p "+passw+" scp -o StrictHostKeyChecking=no platform/ftp_receiver.py "+uname+"@"+ip+":platform/ftp_receiver.py")
	# os.system("sshpass -p "+passw+" scp -o StrictHostKeyChecking=no platform/nfs_client_new.sh "+uname+"@"+ip+":platform/nfs_client_new.sh")
	# os.system("sshpass -p "+passw+" scp -o StrictHostKeyChecking=no platform/server.py "+uname+"@"+ip+":platform/server.py")
	if(uname != "mypc"):
		os.system("sshpass -p "+passw+" scp -o StrictHostKeyChecking=no ~/nfs_client_new.sh "+uname+"@"+ip+":nfs_client_new.sh")
		if(ip not in nfs_queue):		
			print ("Activating NFS on",ip,uname)
			# os.system("sshpass -p "+passw+" ssh  "+uname+"@"+ip+" 'nohup sh ~/nfs/platform/nfs_client_new.sh "+passw+" &> nfs_logs'")
			nfs_queue.append(ip)
			time.sleep(3)
	print ("Activating FTP on",ip,uname)
	os.system("sshpass -p "+passw+" ssh  "+uname+"@"+ip+" 'nohup python3 ~/nfs/platform/ftp_receiver.py "+ip+" &> ftp_logs' &")
	print ("Activating Server")
	os.system("sshpass -p "+passw+" ssh "+uname+"@"+ip+" 'nohup python3 ~/nfs/platform/server.py &> server_logs' &")
	time.sleep(2)
	