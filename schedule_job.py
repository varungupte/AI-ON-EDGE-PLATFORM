import os
import sys
import pika
import json
import urllib2
import pymongo
import xmltodict
sched_dict={}
str_param=sys.argv[1]

str_param=str_param.split("^%^")

sched_dict['req_type']=str_param[0]
sched_dict['service_id']=str_param[1]
sched_dict['app_id']=str_param[2]
sched_dict['num_times']=str_param[3]
sched_dict['start_timestamp']=str_param[4]
sched_dict['duration']=str_param[5]
sched_dict['time_interval']=str_param[6]
sched_dict['run_dependent']=str_param[7]

file_name = os.path.expanduser("~/nfs/platform/platform_configs/platform_config.xml")
config_file=open(file_name,"r")
data=config_file.read()
config_file.close()
data=xmltodict.parse(data)
runner_ip=data['platform']['rabbit_server_ip']
lb_ip=data['platform']['loader']
scheduler_ip=data['platform']['scheduler_ip']
mongodb=data['platform']['mongodb']
threshold=float(data['platform']['threshold'])
replica=int(data['platform']['replica_count'])
deploy_manager_ip=data['platform']['deploy_manager_ip']

scheduler_queue_name = 'scheduler-'+scheduler_ip



def get_command_json(params):

    type = params['req_type']

    req = {}
    req['req_details'] = {}
    req['run_dependent'] = params['run_dependent']

    if type == 'start_now':
        req['req_details']['service_id'] = params['service_id']
        req['req_details']['app_id'] = params['app_id']
        
        req['req_type'] = 'now'
        req['req_details']['stop'] = 'false'
            # req['req_details']['model_name'] = ''

    elif type == 'stop_now':
        req['req_details']['service_id'] = params['service_id']
        req['req_details']['app_id'] = params['app_id']

        req['req_type'] = 'now'
        req['req_details']['stop'] = 'true'

    elif type == 'interval_specific':
        req['req_details']['service_id'] = params['service_id']
        req['req_details']['app_id'] = params['app_id']

        req['req_type'] = 'interval_specific'
        req['req_details']['num_times'] = int(params['num_times'])
        req['req_details']['start_timestamp'] = params['start_timestamp']
        req['req_details']['duration'] = int(params['duration'])
        req['req_details']['time_interval'] = int(params['time_interval'])
        # req['req_details']['model_name'] = '0'

    elif type == 'independent':
        req['req_details']['service_ids'] = params['service_id'].split(' ')
        req['req_details']['app_ids'] = params['app_id'].split(' ')

        req['req_type'] = 'independent'
        req['req_details']['start_timestamps'] = params['start_timestamp'].split(' ')
        req['req_details']['durations'] = params['duration'].split(' ')
        # req['req_details']['model_name'] = '0'
    return req

request = get_command_json(sched_dict)

request = {
            'msg_type': 'scheduleServices',
            'request_by': 'deployManager',
            'data':
            {
                'requests':
                [
                    request
                ]
            }
          }

connection = pika.BlockingConnection(pika.ConnectionParameters(host=runner_ip))
channel = connection.channel()
channel.queue_declare(queue=scheduler_queue_name,auto_delete=True)
channel.basic_publish(exchange='', routing_key=scheduler_queue_name, body=json.dumps(request))
