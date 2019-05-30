import time
from threading import Thread
import pika
import json
from subprocess import Popen, PIPE
import socket
import errno
import shlex
import random
import psutil
import pprint
import os
import urllib.request as urllib2
import pymongo
import subprocess

def append_logs(data):
	f=open("server_logs","a+")
	try:
		f.write(data+"\n")
	except Exception as e:
		f.write(str(e)+"\n")
	f.close()


def find_self_ip():
    GET_IP_CMD ="hostname -I"
    def run_cmd(cmd):
         return subprocess.check_output(cmd, shell=True).decode('utf-8')
    ip = run_cmd(GET_IP_CMD)
    ip2=ip.split(" ")
    return ip2[0]

response = urllib2.urlopen("https://raw.githubusercontent.com/Annu4git/Tools/master/platform_config.txt")
page_source = response.read().decode()

pp=page_source.split('\n')
pp.remove('')
for i in pp:
	t=i.split(' ')

myclient = pymongo.MongoClient(t[t.index('mongodb')+1])
database = myclient["metadata"]
service_metadata = database["service_metadata"]

debug = False

runner_ip = t[t.index('rabbit_server_ip')+1]
#self_ip = find_self_ip()
self_ip = find_self_ip()
service_port_mapping = {}
service_count = 3
exc_cpu = 0.0
exc_mem = 0.0
isExclusiveServer = False

def get_cpu_performance():
    test_output = os.system("sysbench cpu --cpu-max-prime=2000 run | grep 'events per second:' > dump.txt")
    with open('dump.txt','r') as f:
        test_output = f.readline().split('\n')[0].split(' ')[-1]
    print('CPU benchmark:',test_output)
    append_logs('CPU benchmark:'+test_output)	
    return test_output

cpu_benchmark = get_cpu_performance()

def free_ports(num_ports):
    counter = num_ports
    ports = set()
    while counter > 0:
        rport = random.randint(2000,65535)
        port_binded = False
        for r in service_port_mapping:
            if rport == service_port_mapping[r]:
                port_binded = True
                break
        if (rport not in ports) and port_binded == False:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.bind(("127.0.0.1", rport))
                ports.add(str(rport))
                counter-=1
            except socket.error as e:
                continue
            s.close()
    return ' '.join(list(ports))


def receiveRequests():
    global exc_cpu, exc_mem, isExclusiveServer
    def service_manager(ch, method, props, body):
        global exc_cpu, exc_mem, isExclusiveServer
        rec_data = json.loads(body.decode())
        if rec_data['msg_type'] == 'acquire_resources' and rec_data['request_by'] == 'loadBalancer':
            exc_cpu = rec_data['data']['cpu_percent']
            exc_mem = rec_data['data']['mem_free']
            isExclusiveServer = True
        elif rec_data['msg_type'] == 'bind_port' and rec_data['request_by'] == 'deployManager':
            free_port = free_ports(1)
            app_id = rec_data['data']['application_id']
            service_id = rec_data['data']['service_id']
            service_port_mapping[app_id+"$:$"+service_id] = free_port
            
            print('\n\n')
            print('....................Port binded successfully.........................')
            print(rec_data)
            print('\n\n')
            append_logs('Port binded successfully....')		

            print('Updating the database')
            append_logs('Updating the database')	
            update_query = { "service_id": service_id, "application_id": app_id }
            mydoc = service_metadata.find(update_query)

            for x in mydoc:
                node_ips = x['node_ips']
                break

            updated_node_ips = node_ips+" "+self_ip+":"+free_port
            updated_node_ips = updated_node_ips.strip()
            service_restURL = self_ip+":"+free_port+"/"+app_id+"/"+service_id
            newvalues = { "$set": { "node_ips": updated_node_ips, "service_state": 'idle' ,'nature_of_service': rec_data['data']['nature_of_service']} }
            print('Query: ',update_query)
            append_logs('Query: '+str(update_query))	
            print('New vals: ',newvalues)
            append_logs('New vals: '+str(newvalues))	
            service_metadata.update_one(update_query, newvalues)

        elif rec_data['msg_type'] == 'scheduleJob' and rec_data['request_by'] == 'loadBalancer':
            print("Received Trigger")
            append_logs("Received Trigger")	
            if rec_data['data']['trigger_type'] == 'start':
                service_id = rec_data['data']['service_id']
                application_id = rec_data['data']['application_id']
                serving_port = service_port_mapping[application_id+'$:$'+service_id]
                
                query = {'service_id': service_id, 'application_id':application_id}
                result = service_metadata.find(query)
                
                if result.count() == 1:
                    for x in result:
                        nature_of_service = x['nature_of_service']
                    
                    if nature_of_service == 'tensorflow_serving':
                        ## Start the job
                        port = str( service_port_mapping[application_id+"$:$"+service_id] )
                        subprocess.Popen(["tensorflow_model_server", "--port="+port, "--model_name="+service_id, "--model_base_path="+os.path.expanduser("~/"+application_id+"/"+service_id)])
                        print('Tensorflow serving job started....')
                        append_logs('Tensorflow serving job started....')
                    elif nature_of_service == 'flask':
                        os.system('python3 '+os.path.expanduser("~/"+application_id+"/"+service_id+"/app.py"))
                
                ##  update database
                print('Updating the database for start')
                append_logs('Updating the database for start')
                
                if result.count() == 1:
                    serving_nodes = ''
                    rest_URL = ''
                    for x in result:
                        serving_nodes = x['serving_nodes']
                        rest_URL = x['rest_url']
                    print(serving_nodes)
                    serving_nodes = serving_nodes+' '+self_ip
                    service_restURL = self_ip+":"+port+"/"+application_id+"/"+service_id
                    rest_URL = rest_URL + '$*$' + service_restURL
                    newvalues = { "$set": { "serving_nodes": serving_nodes, "rest_url": rest_URL, "service_state": 'running' } }
                    service_metadata.update_one(query, newvalues)
                else:
                    print('More than one service with same name stored in the database...')
                    append_logs('More than one service with same name stored in the database...')		

            elif rec_data['data']['trigger_type'] == 'stop':
                service_id = rec_data['data']['service_id']
                application_id = rec_data['data']['application_id']

                ## Stop the job
                port = str( service_port_mapping[application_id+"$:$"+service_id] )
                for proc in psutil.process_iter():
                    if proc.name() == 'tensorflow_model_server' and proc.cmdline()[1] == '--port='+port:
                        try:
                            pid = proc.as_dict(attrs=['pid'])['pid']
                        except psutil.NoSuchProcess:
                            pass
                        else:
                            if pid != os.getpid():
                                subprocess.run(["sudo", "kill", str(pid)])
                                print('Job stopped....')
                                append_logs('Job stopped....')
                    if proc.name() == 'python3' and proc.cmdline()[1] == application_id+'$:$'+service_id+'.py':
                        try:
                            pid = proc.as_dict(attrs=['pid'])['pid']
                        except psutil.NoSuchProcess:
                            pass
                        else:
                            if pid != os.getpid():
                                subprocess.run(["sudo", "kill", str(pid)])
                                print('Job stopped....')
                                append_logs('Job stopped....')

                ##  update database
                print('Updating the database for stop')
                append_logs('Updating the database for stop')
                query = {'service_id': service_id, 'application_id':application_id}
                result = service_metadata.find(query)
                if result.count() == 1:
                    self_rest_url = self_ip+":"+port+"/"+application_id+"/"+service_id
                    for x in result:
                        serving_nodes = x['serving_nodes'].split(' ')
                        rest_URLs = x['rest_url'].split('$*$')
                    rest_URLs.remove(self_rest_url)
                    serving_nodes.remove(self_ip)
                    if '' in serving_nodes:
                        serving_nodes.remove('')
                    if '' in rest_URLs:
                        rest_URLs.remove('')
                    if len(rest_URLs) == 0 and len(serving_nodes) == 0:
                        newvalues = { "$set": { "serving_nodes": '', "rest_url": '', "service_state": 'stopped' } }
                    else:
                        rest_URLs = '$*$'.join(rest_URLs)
                        serving_nodes = ' '.join(serving_nodes)
                        newvalues = { "$set": { "serving_nodes": serving_nodes, "rest_url": rest_URLs } }
                    service_metadata.update_one(query, newvalues)
                else:
                    print('More than one service with same name stored in the database...')
                    append_logs('More than one service with same name stored in the database...')			


    ip_queue_name = 'server-'+self_ip
    ip_connection = pika.BlockingConnection(pika.ConnectionParameters(host=runner_ip))
    ip_channel = ip_connection.channel()
    ip_channel.queue_declare(queue=ip_queue_name, auto_delete = True)

    ip_channel.basic_consume(on_message_callback=service_manager, queue=ip_queue_name)
    ip_channel.start_consuming()


class BgHeartbeat(object):
    def __init__(self):
        thread = Thread(target=self.run, args=())
        self.configDetails = self.readFromConfig()
        thread.deamon = True
        thread.start()

    def readFromConfig(self):
        configData = {}
        configData['ip'] = self_ip
        configData['layer'] = '1'
        configData['node_type'] = 'server'
        return configData

    def get_exitcode_stdout_stderr(self, cmd):
        args = shlex.split(cmd)
        proc = Popen(args, stdout=PIPE, stderr=PIPE)
        out, err = proc.communicate()
        exitcode = proc.returncode

        return exitcode, out.decode(), err.decode()

    def run(self):
        global service_count, exc_mem, exc_cpu, isExclusiveServer

        queue_name = 'logging_queue'
        connection1 = pika.BlockingConnection(pika.ConnectionParameters(host=runner_ip))
        channel1 = connection1.channel()
        channel1.queue_declare(queue=queue_name, auto_delete = True)


        while True:
            free_memory_gb = psutil.virtual_memory().free / (1073741824.) - exc_mem
            free_mem_percent = free_memory_gb / (free_memory_gb + psutil.virtual_memory().used / (1073741824.))
            free_cpu_percent = 100 - psutil.cpu_percent(interval=None) - exc_cpu

            current_temp = psutil.sensors_temperatures(fahrenheit=False)['acpitz'][0].current
            high_temp = psutil.sensors_temperatures(fahrenheit=False)['acpitz'][0].high

            # print(exc_cpu, exc_mem, isExclusiveServer)
            serving_data = {}
            serving_data['msg_type'] = 'Heartbeat'
            serving_data['ip'] = self.configDetails['ip']
            serving_data['node_type'] = self.configDetails['node_type']
            serving_data['layer'] = self.configDetails['layer']
            serving_data['data'] = {}
            serving_data['data']['isExclusiveServer'] = isExclusiveServer
            serving_data['data']['service_count'] = service_count
            # serving_data['data']['num_cpus'] = num_cpus
            # serving_data['data']['max_clock'] = max_cpu_freq
            if current_temp != None:
                serving_data['data']['temp_current'] = current_temp
            else:
                serving_data['data']['temp_current'] = 50
                
            if high_temp != None:
                serving_data['data']['temp_high'] = high_temp
            else:
                serving_data['data']['temp_high'] = 99
        
            serving_data['data']['temp_high'] = high_temp
            serving_data['data']['cpu_performance'] = cpu_benchmark
            serving_data['data']['cpu_free'] = free_cpu_percent
            serving_data['data']['mem_free'] = free_mem_percent
            serving_data['data']['actual_mem_free'] = free_memory_gb
            services_list = []
            for x in service_port_mapping:
                services_list.append(x+'@#@'+str(service_port_mapping[x]))

            serving_data['data']['deployed_services'] = ' '.join(services_list)

            channel1.basic_publish(exchange='', routing_key=queue_name, body=json.dumps(serving_data))

            time.sleep(2)


bgthread = BgHeartbeat()
receiveRequests()
