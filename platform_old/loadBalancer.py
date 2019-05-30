import pika
import json
import threading
import operator
import pymongo
import time
import urllib.request as urllib2
from retry import retry

response = urllib2.urlopen("https://raw.githubusercontent.com/Annu4git/Tools/master/platform_config.txt")
page_source = response.read().decode()

pp=page_source.split('\n')
pp.remove('')
for i in pp:
	t=i.split(' ')

myclient = pymongo.MongoClient(t[t.index('mongodb')+1])

database = myclient["metadata"]

service_metadata = database["service_metadata"]

nodes_metadata = database["nodes_metadata"]

sensors_metadata = database["sensors_metadata"]

runner_ip = t[t.index('rabbit_server_ip')+1]
replica = int(t[t.index('replica_count')+1])
threshold = float(t[t.index('threshold')+1])

self_ip = t[t.index('loader')+1]

print('Load Balancer ip: ',self_ip)

#self_ip = '10.2.138.136'
server_loads = {}

@retry(pika.exceptions.AMQPConnectionError, delay=5, jitter=(1, 3))
def recieveLoads():
    def onLoadsRecieved(ch, method, props, body):
        global server_loads
        rec_data = json.loads(body.decode())
        #pprint.pprint(rec_data)

        if rec_data['msg_type'] == 'serverLoads':
            server_loads = rec_data['data']
		# elif rec_data['msg_type'] == 'Loads':
		# 	pass
            #pprint.pprint(server_loads)

    queue_name = 'monitoring-loadBalancer'
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=runner_ip))
    loadChannel = connection.channel()
    loadChannel.queue_declare(queue=queue_name, auto_delete = True)

    loadChannel.basic_consume(queue=queue_name, on_message_callback=onLoadsRecieved)
    print('Consume for load started')
    loadChannel.start_consuming()
    connection.close()

def check_temp(curr_temp, high_temp):
    if curr_temp >= high_temp:
        return 0
    else:
        return 1

def compute_score(cpu_percent, memory_percent, cpu_benchmark, free_memory, current_temp, high_temp):
    score = 40. / ( 3./cpu_percent + 1./memory_percent )  # System load
    score *= float(cpu_benchmark)/1e4 + min(2, free_memory)/10.  # System performance
    score *= check_temp(current_temp, high_temp)  # System temperature
    return score



def get_lowest_load_server(layer, req_replica):
    global server_loads

    lowest_load_servers = []

    server_load_score = {}

    print(server_loads)

    #print(layer, server_loads[layer].keys())

    for IP in server_loads[layer].keys():
        if server_loads[layer][IP]['isExclusiveServer'] == False:
            cpu_percent = float( server_loads[layer][IP]['cpu_free'] )
            memory_percent = float( server_loads[layer][IP]['mem_free'] )
            cpu_benchmark = float( server_loads[layer][IP]['cpu_performance'] )
            free_memory = float( server_loads[layer][IP]['actual_mem_free'] )
            current_temp = int( server_loads[layer][IP]['temp_current'] )
            high_temp = int( server_loads[layer][IP]['temp_high'] )

            score = compute_score(cpu_percent, memory_percent, cpu_benchmark, free_memory, current_temp, high_temp)
            server_load_score[IP] = score

    sorted_servers = sorted(server_load_score.items(), key=operator.itemgetter(1))

    print(sorted_servers)

    itr = [len(sorted_servers) if len(sorted_servers) < req_replica else req_replica]

    for i in range(itr[0]):
        if sorted_servers[i][1] > threshold:
            lowest_load_servers.append(sorted_servers[i][0])

    return lowest_load_servers

@retry(pika.exceptions.AMQPConnectionError, delay=5, jitter=(1, 3))
def retrieve_exclusive_nodes(cpu_free_percent, mem_free, cpu_performance):
    global replica, server_loads, runner_ip
    lowest_load_servers = get_lowest_load_server('1', replica)
    
    exclusive_nodes = []

    for server in lowest_load_servers:
        if server_loads['1'][server]['cpu_free'] >= cpu_free_percent and server_loads['1'][server]['actual_mem_free'] >= mem_free and float(server_loads['1'][server]['cpu_performance']) >= float(cpu_performance):
            exclusive_nodes.append(server)

            # Notify these servers to reserve resources for exclusive service that is about to deploy
            sending_data = {}
            sending_data['msg_type'] = 'acquire_resources'
            sending_data['request_by'] = 'loadBalancer'
            sending_data['data'] = {}
            sending_data['data']['cpu_percent'] = cpu_free_percent
            sending_data['data']['mem_free'] = mem_free

            queue_name = 'server-'+server
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=runner_ip))
            loadBalancer_channel = connection.channel()
            loadBalancer_channel.queue_declare(queue=queue_name, auto_delete = True)
            loadBalancer_channel.basic_publish(exchange='', routing_key=queue_name, body=json.dumps(sending_data))

            # Update mapping at loadBalancer
            server_loads['1'][server]['cpu_free'] = server_loads['1'][server]['cpu_free'] - cpu_free_percent
            server_loads['1'][server]['cpu_free'] = server_loads['1'][server]['mem_free'] - mem_free
            server_loads['1'][server]['isExclusiveServer'] = True

            # Update the database

    if len(exclusive_nodes) < replica:
        # num of exclusive nodes to start = replica-exclusive
        print('Required to up new exclusive servers and return its ips')


    return exclusive_nodes

@retry(pika.exceptions.AMQPConnectionError, delay=5, jitter=(1, 3))
def recieveRequests():
    
    @retry(pika.exceptions.AMQPConnectionError, delay=5, jitter=(1, 3))
    def onRequestsRecieved(ch, method, props, body):
        global server_loads, replica
        rec_data = json.loads(body.decode())

        if rec_data['msg_type'] == 'serverLoads':
            server_loads = rec_data['data']
            #if rec_data['msg_type'] == 'Loads':
            #pass
            #pprint.pprint(server_loads)

        elif rec_data['msg_type'] == 'scheduleJobs' and rec_data['request_by'] == 'scheduler':

            service_id = rec_data['data']['service_id']
            application_id = rec_data['data']['application_id']
            locality_tag = rec_data['data']['locality_tag']
            trigger_type = rec_data['data']['trigger_type']

            myquery = { "service_id": service_id, "application_id": application_id }
            mydoc = service_metadata.find(myquery)

            print('Recieved from scheduler')
            
            sensor_query = {"locality_tag": locality_tag}
            sensors_data = sensors_metadata.find(sensor_query)
            input_stream_ips = []
            for sensor in sensors_data:
                input_stream_ips.append(sensor["ip"])
            
            if trigger_type == 'stop':
                query = {'service_id': service_id, 'application_id':application_id}
                result = service_metadata.find(query)
                print('Stopping ',service_id, application_id)
                if result.count() == 1:
                    for x in result:
                        serving_nodes = x['serving_nodes']
                        service_state = x['service_state']
                    if service_state == 'running':
                        sending_data = {}
                        sending_data['msg_type'] = 'scheduleJob'
                        sending_data['request_by'] = 'loadBalancer'
                        sending_data['ip'] = self_ip
                        sending_data['data'] = {}
                        sending_data['data']['service_id'] = service_id
                        sending_data['data']['application_id'] = application_id
                        sending_data['data']['input_stream'] = input_stream_ips
                        sending_data['data']['trigger_type'] = trigger_type
                        
                        print('Retrieved serving nodes for stop: ',serving_nodes)
                        
                        for i in serving_nodes.split(' '):
                            if i!='':
                                service_running_ip = i
                                queue_name = 'server-'+service_running_ip
                                print('sending to: ',i)
                                connection = pika.BlockingConnection(pika.ConnectionParameters(host=runner_ip))
                                loadBalancer_channel = connection.channel()
                                loadBalancer_channel.queue_declare(queue=queue_name, auto_delete = True)
                                loadBalancer_channel.basic_publish(exchange='', routing_key=queue_name, body=json.dumps(sending_data))
                    else:
                        print('No service is running with service_id: ',service_id, ' and application_id: ',application_id)
                elif result.count() > 1:
                    print('More than one service with same name stored in the database...')
                elif result.count() == 0:
                    print('The service ',service_id,' is not stored in the database...')
                
            elif trigger_type == 'start':
                for x in mydoc:
                    deployed_nodes = x['node_ips'].split(' ')
                    deployed_node_ips = []
                    for i in range(len(deployed_nodes)):
                        deployed_node_ips.append(deployed_nodes[i].split(':')[0])
                    service_rest_url = x['rest_url']
    
                    service_priority = x['priority']
                    capable_servers = []
                    isNodeUp = False
                    print('Following are the ips from service metadata')
                    print(deployed_node_ips)
                    for node_ip in deployed_node_ips:
                        if service_priority == "high":
                            l = '1'
                        elif service_priority == "low":
                            l = '0'
                        cpu_percent = float( server_loads[l][node_ip]['cpu_free'] )
                        memory_percent = float( server_loads[l][node_ip]['mem_free'] )
                        cpu_benchmark = float( server_loads[l][node_ip]['cpu_performance'] )
                        free_memory = float( server_loads[l][node_ip]['actual_mem_free'] )
                        current_temp = int( server_loads[l][node_ip]['temp_current'] )
                        high_temp = int( server_loads[l][node_ip]['temp_high'] )
    
                        calc_threshold = compute_score(cpu_percent, memory_percent, cpu_benchmark, free_memory, current_temp, high_temp)
    
                        print(node_ip)
    
                        nodes_query = { "ip": node_ip }
                        responsibleNodes = nodes_metadata.find(nodes_query)
    
                        for node in responsibleNodes:
                            if node['nodeState'] == "active":
                                isNodeUp = True
                                print('Node: ', node_ip, " is responsible node!")
                                break
    
                        print('Threshold is: ',calc_threshold)
    
                        if calc_threshold > threshold and isNodeUp:
                            capable_servers.append((calc_threshold, node_ip))
                        isNodeUp = False
    
    
                    # if any server out of the two is down or unable to handle load
                    if len(capable_servers) == 0:
                        print('Need to shift models to a less loaded server or start new servers....')
                        # lowest_load_servers = get_lowest_load_server(rec_data['data']['layer'])
                        # need to move services across servers
                    else:
                        print('Scheduling start job to the servers....')
                        for server in capable_servers:
                            sending_data = {}
                            sending_data['msg_type'] = 'scheduleJob'
                            sending_data['request_by'] = 'loadBalancer'
                            sending_data['ip'] = self_ip
                            sending_data['data'] = {}
                            sending_data['data']['service_id'] = service_id
                            sending_data['data']['application_id'] = application_id
                            sending_data['data']['input_stream'] = input_stream_ips
                            sending_data['data']['trigger_type'] = trigger_type
                            queue_name = 'server-'+server[1]
                            connection = pika.BlockingConnection(pika.ConnectionParameters(host=runner_ip))
                            loadBalancer_channel = connection.channel()
                            loadBalancer_channel.queue_declare(queue=queue_name, auto_delete = True)
                            loadBalancer_channel.basic_publish(exchange='', routing_key=queue_name, body=json.dumps(sending_data))
                        
                        if len(capable_servers) < replica:
                            print('Start ',replica-len(capable_servers), ' number of servers')


        elif rec_data['msg_type'] == 'deployServices' and rec_data['request_by'] == 'deployManager':

            print('Message Recieved from deploy manager')

            if rec_data['data']['service_type'] == 'exclusive':

                lowest_load_servers = retrieve_exclusive_nodes(rec_data['data']['service_requirement']['cpu_free'],
                                                               rec_data['data']['service_requirement']['mem_free'],
                                                               rec_data['data']['service_requirement']['cpu_performance'])
            elif rec_data['data']['service_type'] == 'normal':
                if rec_data['data']['layer'] == '0':
                    lowest_load_edge = get_lowest_load_server(rec_data['data']['layer'], 1)
                    if len(lowest_load_edge) == 0:
                        lowest_load_servers = get_lowest_load_server('1', replica)
                        if len(lowest_load_servers) < replica:
                            print('Required to up a new server and add its ip to lowest load servers')
                    else:
                        lowest_load_servers = get_lowest_load_server('1', replica-1)
                        if len(lowest_load_servers) < replica-1:
                            print('Required to up a new server and add its ip to lowest load servers')
                        lowest_load_servers.append(lowest_load_edge[0])
                else:
                    lowest_load_servers = get_lowest_load_server(rec_data['data']['layer'], replica)
                    if len(lowest_load_servers) < replica:
                            print('Required to up a new server and add its ip to lowest load servers')

            sending_data = {}
            sending_data['msg_type'] = 'deployServicesResp'
            sending_data['request_by'] = 'loadBalancer'
            sending_data['data'] = {}
            sending_data['data']['lowest_load_servers'] = lowest_load_servers
            sending_data['data']['application_id'] = rec_data['data']['application_id']
            sending_data['data']['service_id'] = rec_data['data']['service_id']
            sending_data['data']['nature_of_service'] = rec_data['data']['nature_of_service']
            sending_data['ip'] = self_ip

            queue_name = 'deployManager-'+rec_data['ip']
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=runner_ip))
            loadBalancer_channel = connection.channel()
            loadBalancer_channel.queue_declare(queue=queue_name, auto_delete = True)
            loadBalancer_channel.basic_publish(exchange='', routing_key=queue_name, body=json.dumps(sending_data))

    queue_name = 'loadBalancer-'+self_ip

    connection = pika.BlockingConnection(pika.ConnectionParameters(host=runner_ip))
    reqChannel = connection.channel()
    reqChannel.queue_declare(queue=queue_name, auto_delete = True)

    reqChannel.basic_consume(queue=queue_name, on_message_callback=onRequestsRecieved)

    print('Consume for other msgs started')

    reqChannel.start_consuming()
    connection.close()

@retry(pika.exceptions.AMQPConnectionError, delay=5, jitter=(1, 3))
def sendHeartbeat():
    while True:
        serving_data = {}
        serving_data['msg_type'] = 'Heartbeat'
        serving_data['ip'] = self_ip
        serving_data['node_type'] = 'loadBalancer'
        queue_name = 'logging_queue'
        connection1 = pika.BlockingConnection(pika.ConnectionParameters(host=runner_ip))
        channel1 = connection1.channel()
        channel1.queue_declare(queue=queue_name, auto_delete = True)
        channel1.basic_publish(exchange='', routing_key=queue_name, body=json.dumps(serving_data))
        time.sleep(2)


thread_recv_loads = threading.Thread(target=recieveLoads, args=())
thread_recv_requests = threading.Thread(target=recieveRequests, args=())
thread_send_heartbeat = threading.Thread(target=sendHeartbeat, args=())
#thread_recv_loads.deamon = True
thread_recv_loads.start()
#thread_recv_requests.daemon = True
thread_recv_requests.start()
#thread_send_heartbeat.daemon = True
thread_send_heartbeat.start()
thread_recv_loads.join()
thread_recv_requests.join()
thread_send_heartbeat.join()
