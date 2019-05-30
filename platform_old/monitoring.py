import threading
import pika
import json
import time
import pprint
import urllib.request as urllib2
import pymongo

response = urllib2.urlopen("https://raw.githubusercontent.com/Annu4git/Tools/master/platform_config.txt") 
page_source = response.read().decode()

pp=page_source.split('\n')
pp.remove('')
for i in pp:
	t=i.split(' ')
    
myclient = pymongo.MongoClient(t[t.index('mongodb')+1])

database = myclient["metadata"]

nodes_metadata = database["nodes_metadata"]

service_metadata = database["service_metadata"]

runner_ip = t[t.index('rabbit_server_ip')+1]


loads = {}
monitor_hb = {}

debug = True

def recieveLoads():
    global loads, monitor_hb
    def onLoadRecieved(ch, method, props, body):
        global loads, monitor_hb
        rec_data = json.loads(body.decode())
        if rec_data['msg_type'] == 'Heartbeat':
            
            nodes_query = { "ip": rec_data['ip'], "subsystem_type": rec_data['node_type'] }
            res = nodes_metadata.find(nodes_query)
            if res.count() == 0:
                nodeEntry = {'ip':rec_data['ip'], 'subsystem_type':rec_data['node_type'], 'nodeState': 'active'}
                x = nodes_metadata.insert_one(nodeEntry)
                print('Inserting to database')
            else:
                for x in res:
                    if x['nodeState'] != 'active':
                        nodes_query = { "ip": rec_data['ip'] , "subsystem_type":rec_data['node_type']}
                        newvalues = { "$set": { "nodeState": 'active' } }          
                        nodes_metadata.update_one(nodes_query, newvalues)
                        print('Updating the database')
                
            if rec_data['node_type'] == 'server':
                print('Logs recieved by the server')
                try:
                    loads[rec_data['layer']][rec_data['ip']] = {}
                    loads[rec_data['layer']][rec_data['ip']] = rec_data['data']
                except KeyError:
                    loads[rec_data['layer']] = {}
                    loads[rec_data['layer']][rec_data['ip']] = {}
                    loads[rec_data['layer']][rec_data['ip']] = rec_data['data']
                print(loads)
                monitor_hb[rec_data['ip']+'@'+rec_data['node_type']] = time.time()
            else:
                print('Logs recieved by the: ',rec_data['node_type'])
                monitor_hb[rec_data['ip']+'@'+rec_data['node_type']] = time.time()
        # elif rec_data['msg_type'] == 'loads':
            # 	pass
        #pprint.pprint(loads)

    queue_name = 'logging_queue'
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=runner_ip))
    logChannel = connection.channel()
    logChannel.queue_declare(queue=queue_name, auto_delete = True)

    logChannel.basic_consume(queue=queue_name, on_message_callback=onLoadRecieved)
    logChannel.start_consuming()
    connection.close()


def publishLoads():
    global loads
    print('Submitting loads to LB')
    while True:
        sending_data = {}
        sending_data['msg_type'] = "serverLoads"
        sending_data['request_by'] = 'monitoringSystem'
        sending_data['data'] = loads
        queue_name = 'monitoring-loadBalancer'
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=runner_ip))
        loadBalancer_channel = connection.channel()
        loadBalancer_channel.queue_declare(queue=queue_name, auto_delete = True)
        loadBalancer_channel.basic_publish(exchange='', routing_key=queue_name, body=json.dumps(sending_data))
        time.sleep(2)

def monitorComponents():
    global monitor_hb
    while True:
        print('Checking logs')
        current_time = time.time()
        for a in monitor_hb:
            if current_time - monitor_hb[a] > 4:
                ip_addr = a.split('@')[0]
                node_type = a.split('@')[1]
                nodes_query = { "ip": ip_addr, "subsystem_type": node_type}
                newvalues = { "$set": { "nodeState": 'down' } }
                nodes_metadata.update_one(nodes_query, newvalues)
                
                if node_type == 'server' or node_type == 'edge':

                    if node_type == 'server':
                        services_applications = loads['1'][ip_addr]['deployed_services'].split(' ')
                    elif node_type == 'edge':
                        services_applications = loads['0'][ip_addr]['deployed_services'].split(' ')                    
                    
                    services_applications.remove('')
                    s_a = {} 
                    print(services_applications)
                    for x in services_applications:
                        s_a[x.split('@#@')[0]] = x.split('@#@')[1]
                        
                    for x in s_a:
                        application_id = x.split('$:$')[0] 
                        service_id = x.split('$:$')[1]
                        port = s_a[x]
                        query = {'service_id': service_id, 'application_id':application_id}
                        self_rest_url = ip_addr+":"+port+"/"+application_id+"/"+service_id
                        result = service_metadata.find(query)
                        if result.count() == 1:
                            for x in result:
                                serving_nodes = x['serving_nodes'].split(' ')
                                rest_URLs = x['rest_url'].split('$*$')
                            if self_rest_url in rest_URLs:
                                rest_URLs.remove(self_rest_url)
                            if ip_addr in serving_nodes:
                                serving_nodes.remove(ip_addr)
                            if len(rest_URLs) == 0 and len(serving_nodes) == 0:
                                newvalues = { "$set": { "serving_nodes": '', "rest_url": '', "service_state": 'stopped' } }                           
                            else:
                                rest_URLs = '$*$'.join(rest_URLs)
                                serving_nodes = ' '.join(serving_nodes)
                                newvalues = { "$set": { "serving_nodes": serving_nodes, "rest_url": rest_URLs, "service_state": 'running' } }
                            service_metadata.update_one(query, newvalues)
                        else:
                            print('More present in db')

                    print(node_type,' is down, bringing it back.....!')
                else:
                    print(node_type,' is down, bringing it back.....!')
                
                
        time.sleep(2)

t1 = threading.Thread(target=recieveLoads)
t2 = threading.Thread(target=publishLoads)
t3 = threading.Thread(target=monitorComponents)
t1.start()
t2.start()
t3.start()
t1.join()
t2.join()
t3.join()
