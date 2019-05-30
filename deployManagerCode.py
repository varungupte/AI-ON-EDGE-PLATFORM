import pika
import json
import os
import threading
import pymongo
import subprocess
import urllib.request as urllib2
import sys
import time
import validation
import xmltodict
import xml_2_json

def toJson(xmlfile):
    datasource = open(xmlfile,'rb')
    o = xmltodict.parse(datasource)
    data = json.dumps(o)
    data = json.loads(data)
    return data



# user_dict={}
# config_file=open("/home/mypc/nfs/platform/platform_configs/platform_servers.xml","r")
# data=
# config_file.close()
# data=xmltodict.parse(data)
# print (data['platform_servers']['servers']['server'][0])
ip_pass_data =toJson("/home/mypc/nfs/platform/platform_configs/platform_servers.xml") 
        
print(ip_pass_data)

user_dict={}

print (ip_pass_data['platform_servers']['servers']['server'])

for node in ip_pass_data['platform_servers']['servers']['server']:
    # print ("___",node)
    # print ("++",type(node))
    node_password = node['password']
    node_uname = node['uname']
    user_dict[node['ip']]=[node_uname,node_password]


for node in ip_pass_data['platform_servers']['edges']['edge']:

    node_password = node['password']
    node_uname = node['uname']
    user_dict[node['ip']]=[node_uname,node_password]












'''
for i in data['platform_servers']['servers']['server']:
    passw=i['password']
    uname=i['uname']
    ip=i['ip']
    user_dict[ip]=[uname,passw]

for i in data['platform_servers']['edges']['edge']:
    passw=i['password']
    uname=i['uname']
    ip=i['ip']
    user_dict[ip]=[uname,passw]
'''



config_file=open("/home/mypc/nfs/platform/platform_configs/platform_config.xml","r")
data=config_file.read()
config_file.close()
data=xmltodict.parse(data)




def find_self_ip():
    GET_IP_CMD ="hostname -I"
    def run_cmd(cmd):
         return subprocess.check_output(cmd, shell=True).decode('utf-8')
    ip = run_cmd(GET_IP_CMD)
    ip2=ip.split(" ")
    return ip2[0]



self_ip = find_self_ip()
runner_ip=data['platform']['rabbit_server_ip']
lb_ip=data['platform']['loader']
scheduler_ip=data['platform']['scheduler_ip']
mongodb=data['platform']['mongodb']
threshold=data['platform']['threshold']
replica_count=data['platform']['replica_count']
deploy_manager_ip=data['platform']['deploy_manager_ip']

myclient = pymongo.MongoClient(mongodb)
database = myclient["metadata"]
service_metadata = database["service_metadata"]
request_metadata = database["request_metadata"]
nodes_metadata = database["nodes_metadata"]


print ("runner_ip",runner_ip)
print ("self_ip",self_ip)
print ("lb_ip",lb_ip)
print ("replica_count",replica_count)
print ("threshold",threshold)




def askDeployInfo(model,app,self_ip,lb_ip,runner_ip,origin,service_data):
    global nodes_metadata
    loads = {}
    if origin == 'App':
        model = model.split(".zip")[0]
    else:
        model = model.split(".py")[0]

    print (service_data['services']['service'])

    print("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")

    services=service_data['services']['service']


    found = False

    for service in services:
        print ("++",service)
        if service!=None and service['service_name'] == model and service['application_name'] == app:
            loads['msg_type'] = 'deployServices'
            loads['request_by'] = 'deployManager'
            loads['data'] = {}
            loads['data']['layer'] = service['priority_index']
            loads['ip'] = self_ip
            loads['data']['service_id'] = model
            loads['data']['application_id'] = app
            loads['data']['service_type']=service['service_type']
            loads['data']['service_requirement']={}
            # loads['data']['replica_count']=service['replica_count']
            try:
                loads['data']['service_requirement']['cpu_free']=float(service['exclusive_details']['cpu_free'])
            except:
                loads['data']['service_requirement']['cpu_free']=0

            try:
                loads['data']['service_requirement']['mem_free']=float(service['exclusive_details']['memory_free'])
            except:
                loads['data']['service_requirement']['mem_free']=0
            try:    
                loads['data']['service_requirement']['cpu_performance']=float(service['exclusive_details']['cpu_benchmark'])
            except:
                loads['data']['service_requirement']['cpu_performance']=0



            loads['data']['origin']=origin
            if service['priority_index'] == '0':
                location_tag = service['location_tag']
                query = {'subsystem_type':'edge', 'location_tag': location_tag}
                result = nodes_metadata.find(query)
                for x in result:
                    loads['data']['edge_ip'] = x['ip']
                    print (x['ip'],"**************************************************")
            loads['data']['nature_of_service'] = service['nature_of_service']
            loads['data']['isDependent']=service['isDependent']
            loads['data']['dependent_sequence']=service['dependent_sequence']['sequence']
            loads['data']['output_stream']=service['output_stream']
            loads['data']['scheduling_info']=service['scheduling_info']

            found = True

    if not found:
        print('----------------------------------------\n\n')
        print(model, app)
        print('----------------------------------------\n\n')

    queue_name = 'loadBalancer-'+lb_ip
    #print('Queue is: ',queue_name)
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=runner_ip))
    loadBalancer_channel = connection.channel()
    loadBalancer_channel.queue_declare(queue=queue_name,auto_delete=True)
    loadBalancer_channel.basic_publish(exchange='', routing_key=queue_name, body=json.dumps(loads))
    #print('Published')
   
def send_to_scheduler(info):
    global scheduler_ip

    req = {}
    req['req_details'] = {}

    req['req_details']['service_id'] = info['service_id']
    req['req_details']['app_id'] = info['application_id']

    req['req_type'] = 'interval_specific'
    req['req_details']['num_times'] = int(info['num_times'])
    req['req_details']['start_timestamp'] = info['start_at']
    req['req_details']['duration'] = int(info['duration'])
    req['req_details']['time_interval'] = int(info['time_interval'])

    request = {
                'msg_type': 'scheduleServices',
                'request_by': 'deployManager',
                'data':
                {
                    'requests': [req]
                }
              }
    queue_name = 'scheduler-'+scheduler_ip
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=runner_ip))
    loadBalancer_channel = connection.channel()
    loadBalancer_channel.queue_declare(queue=queue_name,auto_delete=True)
    loadBalancer_channel.basic_publish(exchange='', routing_key=queue_name, body=json.dumps(request))




def recieveDeployInfo():
    def onMsgRecieved(ch, method, props, body):
        global user_dict
        rec_data = json.loads(body.decode())
        
        if rec_data['msg_type'] == 'deployServicesResp' and rec_data['request_by'] == 'loadBalancer':
            print('Updating the database')
            
            #{"msg_type": "deployServicesResp", "request_by": "loadBalancer", "data": {"lowest_load_servers": ["10.2.138.136"], "application_id": "a-002", "service_id": "s-001"}, "ip": "10.2.138.136"}'
            
            print("######################")
            print(rec_data)
            print("######################")
            db_nodes_data = ' '.join(rec_data['data']['lowest_load_servers'])
            print('IP: ',db_nodes_data)

            #-----------------------------------------------
            # if(db_nodes_data==""):
            #     f=open("IAS_UI/dmc_log","w")
            #     f.write("Insufficient Machines to deploy '"+rec_data['data']['service_id']+"'' ! Add more computers to continue.")
            #     f.close()
            #-----------------------------------------------

            all_ips=db_nodes_data.split(' ')

            #############################
            for ip in all_ips:
                destination_ip=ip.split(':')[0]
                try:
                    passw=user_dict[destination_ip][1]
                except:
                    print ("No Resources")
                    exit(0)
                uname=user_dict[destination_ip][0]
                application=rec_data['data']['application_id']
                
                os.system("sshpass -p "+passw+" ssh -o StrictHostKeyChecking=no "+uname+"@"+destination_ip+" 'mkdir -p "+application_name+"/App'")
                os.system("sshpass -p "+passw+" ssh -o StrictHostKeyChecking=no "+uname+"@"+destination_ip+" 'mkdir -p "+application_name+"/Services'")
                if(rec_data['data']['origin']=="App"):
                    model=rec_data['data']['service_id']+".zip"
                    print("Sending",model,"of",application_name,"to",destination_ip,uname)
                    print("--")
                    os.system("python2 /home/mypc/Desktop/final_demo/ftp_sender.py applications/"+application_name+"/App/"+model+" "+destination_ip+" "+application_name+"/App")
                    print ("Im here")
                    os.system("wait")
                
                if(rec_data['data']['origin']=="Services"):
                    model=rec_data['data']['service_id']+".py"
                    print("Sending",model,"of",application_name,"to",destination_ip,uname)
                    print("--")
                    os.system("python2 /home/mypc/Desktop/final_demo/ftp_sender.py applications/"+application_name+"/Services/"+model+" "+destination_ip+" "+application_name+"/Services")
                    print ("Im also here")
                    os.system("wait")
                
                os.system("python2 /home/mypc/Desktop/final_demo/ftp_sender.py applications/"+application_name+"/application.config "+destination_ip+" "+application_name)
                os.system("python2 /home/mypc/Desktop/final_demo/ftp_sender.py applications/"+application_name+"/service.config "+destination_ip+" "+application_name)


                
            print('Ask nodes to bind port with particular service')

            print("H1")
            sending_data = {}
            print("H1")
            sending_data['msg_type'] = 'bind_port'
            print("H1")
            sending_data['request_by'] = 'deployManager'
            print("H1")
            sending_data['data'] = {}
            sending_data['data']['service_id'] = rec_data['data']['service_id']
            sending_data['data']['application_id'] = rec_data['data']['application_id']
            sending_data['data']['nature_of_service'] = rec_data['data']['nature_of_service']
            sending_data['data']['isDependent']=rec_data['data']['isDependent']
            # sending_data['data']['replica_count']=rec_data['data']['replica_count']
            print("H1")
            sending_data['data']['dependent_sequence']=rec_data['data']['dependent_sequence']
            print("H1")
            sending_data['data']['output_stream']=rec_data['data']['output_stream']

            print ("&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&")
            print (rec_data)
            print ("&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&")
            for node in rec_data['data']['lowest_load_servers']:

                query = {'ip':node,'subsystem_type':'server'}
                if nodes_metadata.find(query).count() == 1:
                    server_queue_name = 'server-'+node
                elif nodes_metadata.find(query).count() == 0:
                    query = {'ip':node, 'subsystem_type':'edge'}
                    if nodes_metadata.find(query).count() == 1:
                        server_queue_name = 'edge-'+node

                # if(rec_data['data']['layer']=="1"):
                #     server_queue_name = 'server-'+node
                # else:
                #     server_queue_name = 'edge-'+node

                print (server_queue_name)
                connection = pika.BlockingConnection(pika.ConnectionParameters(host=runner_ip))
                loadBalancer_channel = connection.channel()
                loadBalancer_channel.queue_declare(queue=server_queue_name,auto_delete=True)
                loadBalancer_channel.basic_publish(exchange='', routing_key=server_queue_name, body=json.dumps(sending_data))
                # time.sleep(1)

            sched_info = rec_data['data']['scheduling_info']
            if sched_info and sched_info['start_at'] != None:
                sched_info['service_id'] = rec_data['data']['service_id']
                sched_info['application_id'] = rec_data['data']['application_id']
                send_to_scheduler(sched_info)


        print('Message Recieved')
        
    
    queue_name = 'deployManager-'+self_ip
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=runner_ip))
    reqChannel = connection.channel()
    reqChannel.queue_declare(queue=queue_name,auto_delete=True)
    reqChannel.basic_consume(queue=queue_name, on_message_callback=onMsgRecieved)
    reqChannel.start_consuming()
    connection.close()

######################################




application_name=sys.argv[1]
application_zip_location="/home/mypc/Desktop/final_demo/applications/"+application_name+".zip"


import zipfile
zip_ref = zipfile.ZipFile(application_zip_location, 'r')
zip_ref.extractall("applications/")
zip_ref.close()

#-------------------------------------------------------------------------------------


file_name="applications/"+application_name+"/service.config"

service_data=json.loads(xml_2_json.tojson(file_name))










#-------------------------------------------------------------------------------------

thread_recv_loads = threading.Thread(target=askDeployInfo, args=())
thread_recv_requests = threading.Thread(target=recieveDeployInfo, args=())
thread_recv_requests.start()



available_model_names=os.listdir("applications/"+application_name+"/App")
print (available_model_names)

# print (service_data,"++++")
# print (service_data['services']['service']['service_name'],"++++")
# print (service_data,"++++")

print(service_data['services']['service'])



for i in available_model_names:

    for x in service_data['services']['service']: 
        if(x['service_name']==i.split(".zip")[0] and x['priority_index'] == '0'):
            # print(i)
            # print("This Service is Meant for Edge, and will be sent to NFS.")
            # os.system("mkdir -p ~/nfs/Edge_Models/"+application_name)
            # os.system("mkdir -p ~/nfs/Edge_Models/"+application_name+"/App/")
            # os.system("cp -f /home/mypc/Desktop/final_demo/applications/"+application_name+"/"+i+" ~/nfs/Edge_Models/"+application_name+"/App/")
            # os.system("unzip ~/nfs/Edge_Models/"+application_name+"/App/"+i)
            # print x['location_tag']
            model=i
            myquery = { "service_id": model, "application_id": application_name }
            mydoc = service_metadata.find(myquery)
            if mydoc.count() == 0:
                serviceEntry = {"node_ips":"", "service_id": model.split(".zip")[0], "application_id": application_name, "rest_url":"", "priority":"low", "location_tag":x['location_tag'],"scheduling_info":{},"serving_nodes":"","service_state":"","is_dependent":"false","dependent_sequence":[],"nature_of_service":"", "output_stream":"","replica_count":int(x['replica_count'])}
                #x = service_metadata.insert_one(serviceEntry)
                rEntry = {"app_service_id":model.split(".zip")[0]+"$:$"+application_name, "counter": -1}
                x = service_metadata.insert_one(serviceEntry)
                y = request_metadata.insert_one(rEntry)
                print ("Adding to Database")
            askDeployInfo(model,application_name,self_ip,lb_ip,runner_ip,"App",service_data)
        elif x['service_name']==i.split(".zip")[0] and x['priority_index'] == '1':
            model=i
            myquery = { "service_id": model, "application_id": application_name }
            mydoc = service_metadata.find(myquery)
            if mydoc.count() == 0:
                serviceEntry = {"node_ips":"", "service_id": model.split(".zip")[0], "application_id": application_name, "rest_url":"", "priority":"high", "location_tag":x['location_tag'],"scheduling_info":{},"serving_nodes":"","service_state":"","is_dependent":"false","dependent_sequence":[],"nature_of_service":"", "output_stream":"","replica_count":int(x['replica_count'])}
                #x = service_metadata.insert_one(serviceEntry)
                rEntry = {"app_service_id":model.split(".zip")[0]+"$:$"+application_name, "counter": -1}
                x = service_metadata.insert_one(serviceEntry)
                y = request_metadata.insert_one(rEntry)
                print ("Adding to Database")

            askDeployInfo(model,application_name,self_ip,lb_ip,runner_ip,"App",service_data)





available_service_names=os.listdir("applications/"+application_name+"/Services")
print (available_service_names)


for i in available_service_names:
        model=i
        myquery = { "service_id": model, "application_id": application_name }
        mydoc = service_metadata.find(myquery)

        if mydoc.count() == 0:
            serviceEntry = {"node_ips":"", "service_id": model.split(".py")[0], "application_id": application_name, "rest_url":"", "priority":"high", "input_stream_tag":"india/uk/haridwar","scheduling_info":{},"serving_nodes":"","service_state":"","is_dependent":"false","dependent_sequence":[],"nature_of_service":"", "output_stream":""}
            #x = service_metadata.insert_one(serviceEntry)
            rEntry = {"app_service_id":model.split(".py")[0]+"$:$"+application_name, "counter": -1}
            x = service_metadata.insert_one(serviceEntry)
            y = request_metadata.insert_one(rEntry)
            print ("Adding to Database")
        askDeployInfo(model,application_name,self_ip,lb_ip,runner_ip,"Services",service_data)

	

		
thread_recv_requests.join()

#######################################


