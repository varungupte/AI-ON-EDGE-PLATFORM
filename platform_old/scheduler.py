from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.jobstores.mongodb import MongoDBJobStore
import time
import datetime
import threading
import pika
import sys
import json
import urllib.request as urllib2
import subprocess
import pprint

response = urllib2.urlopen("https://raw.githubusercontent.com/Annu4git/Tools/master/platform_config.txt")
page_source = response.read().decode()

pp=page_source.split('\n')
pp.remove('')
for i in pp:
    t=i.split(' ')

debug = False

## TODOS
# Take IP from databse and use it to stop the service
# receive acks
# save state
# load state

def find_self_ip():
    GET_IP_CMD ="hostname -I"
    def run_cmd(cmd):
         return subprocess.check_output(cmd, shell=True).decode('utf-8')
    ip = run_cmd(GET_IP_CMD)
    ip2=ip.split(" ")
    return ip2[0]
find_self_ip()

self_ip = t[t.index('scheduler_ip')+1]

runner_ip = t[t.index('rabbit_server_ip')+1]

LB_IP = t[t.index('loader')+1]
lb_queue_name = 'loadBalancer-'+LB_IP
ip_queue_name = 'scheduler-'+self_ip

if not debug:
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=runner_ip))
    lb_channel = connection.channel()
    lb_channel.queue_declare(queue=lb_queue_name, auto_delete = True)

    ip_connection = pika.BlockingConnection(pika.ConnectionParameters(host=runner_ip))
    ip_channel = ip_connection.channel()
    ip_channel.queue_declare(queue=ip_queue_name, auto_delete = True)



def receive_callback(ack_serving_obj, queue_name):
    def ack_callback(ch, method, props, body):
        print("RECEIVED CALLBACK")
        print('ACKNOWLEDGEMENT RECEIVED')
    ack_serving_obj.basic_consume(ack_callback, queue=queue_name, no_ack=True)
    ack_serving_obj.start_consuming()


def job(req_type, service_id, app_id, ip_stream_addr, stop=False):

    data = {
            'msg_type': 'scheduleJobs',
            'request_by': 'scheduler',
            'data': {
                    'service_id': service_id,
                    'application_id': app_id,
                    'locality_tag': ip_stream_addr
                    },
            }

    if stop:
        data['data']['trigger_type'] = 'stop'
    else:
        data['data']['trigger_type'] = 'start'

    if not debug:
        lb_channel.basic_publish(exchange='', routing_key=lb_queue_name, body=json.dumps(data))

    if stop:
        print("stop application "+str(app_id)+"'s service "+str(service_id))

    else:
        print("trigger application "+str(app_id)+"'s service "+str(service_id))



def schedule_job(req):
    global job

    if req['req_type'] == 'interval_specific':
        sec = req['req_details']['time_interval']
        n = req['req_details']['num_times']
        service_id = req['req_details']['service_id']
        app_id = req['req_details']['app_id']
        start_time_str = req['req_details']['start_timestamp']
        input_stream_addr = req['req_details']['input_stream_addr']
        duration = req['req_details']['duration']

        start_at = datetime.datetime.now() + datetime.timedelta(seconds=0.05)
        start_sec = 0

        if start_time_str == '0':
            if n == 0:
                sched.add_job(job, 'interval', args=[req['req_type'], service_id, app_id, input_stream_addr], seconds=sec, next_run_time=start_at)

            else:
                repeat_till = start_at + datetime.timedelta(seconds=(n-1)*sec+0.1)
                sched.add_job(job, 'interval', args=[req['req_type'], service_id, app_id, input_stream_addr], seconds=sec, next_run_time=start_at, end_date=repeat_till)

        else:
            start_at = datetime.datetime.strptime(start_time_str, '%Y:%m:%d:%H:%M:%S')

            # If provided start time is past, start now!
            if (start_at - datetime.datetime.now()).total_seconds() < 0:
                start_at = datetime.datetime.now() + datetime.timedelta(seconds=0.05)

            if n == 0:
                sched.add_job(job, 'interval', args=[req['req_type'], service_id, app_id, input_stream_addr], seconds=sec, next_run_time=start_at)

            else:
                repeat_till = start_at + datetime.timedelta(seconds=(n-1)*sec+0.1)
                sched.add_job(job, 'interval', args=[req['req_type'], service_id, app_id, input_stream_addr], seconds=sec, next_run_time=start_at, end_date=repeat_till)


        if req['input_type'] == 'stream':
            stop_at = start_at + datetime.timedelta(seconds=duration)

            if n == 0:
                sched.add_job(job, 'interval', args=[req['req_type'], service_id, app_id, input_stream_addr, True], seconds=sec, next_run_time=stop_at)

            else:
                stop_till = stop_at + datetime.timedelta(seconds=(n-1)*sec)
                sched.add_job(job, 'interval', args=[req['req_type'], service_id, app_id, input_stream_addr, True], seconds=sec, next_run_time=stop_at, end_date=stop_till)


###########
    if req['req_type'] == 'dependent':
        interval = req['req_details']['time_intervals']
        start_time_str = req['req_details']['initial_timestamp']

        service_id = req['req_details']['service_ids'][0]
        app_id = req['req_details']['app_ids'][0]
        input_stream_addr = req['req_details']['input_stream_addrs'][0]

        start_at = datetime.datetime.now() + datetime.timedelta(seconds=0.05)

        if start_time_str == '0':
            sched.add_job(job, 'date', args=[req['req_type'], service_id, app_id, input_stream_addr], next_run_time=start_at)

        else:
            start_at = datetime.datetime.strptime(start_time_str, '%Y:%m:%d:%H:%M:%S')

            # If provided start time is past, start now!
            if (start_at - datetime.datetime.now()).total_seconds() < 0:
                start_at = datetime.datetime.now() + datetime.timedelta(seconds=0.05)

            sched.add_job(job, 'date', args=[req['req_type'], service_id, app_id, input_stream_addr], next_run_time=start_at)


        if req['input_type'] == 'stream':
            duration = req['req_details']['durations'][0]
            stop_at = start_at + datetime.timedelta(seconds=duration)
            sched.add_job(job, 'date', args=[req['req_type'], service_id, app_id, input_stream_addr, True], next_run_time=stop_at)


        idx = 1
        for i in interval:
            service_id = req['req_details']['service_ids'][idx]
            app_id = req['req_details']['app_ids'][idx]
            input_stream_addr = req['req_details']['input_stream_addrs'][idx]

            start_at = datetime.datetime.now() + datetime.timedelta(seconds=0.05)
            sched.add_job(job, 'date', args=[req['req_type'], service_id, app_id, input_stream_addr], next_run_time=start_at)

            if req['input_type'] == 'stream':
                duration = req['req_details']['durations'][idx]
                stop_at = start_at + datetime.timedelta(seconds=duration)
                sched.add_job(job, 'date', args=[req['req_type'], service_id, app_id, input_stream_addr, True], next_run_time=stop_at)

            if not debug:
                pass
                # receive_callback(mapping[service_id]['ack_queue_obj'], mapping[service_id]['ack_queue_name'])

            idx += 1
############
            # schedule.run_pending()
            # response= wait for socket to respond

            #receive_callback(mapping[service_id]['ack_queue_obj'], mapping[service_id]['ack_queue_name'])

###########
    if req['req_type'] == 'independent':
        sec = 0
        idx = 0
        for service_id in req['req_details']['service_ids']:
            start_time_str = req['req_details']['start_timestamps'][idx]
            input_stream_addr = req['req_details']['input_stream_addrs'][idx]
            app_id = req['req_details']['app_ids'][idx]

            start_at = datetime.datetime.now() + datetime.timedelta(seconds=0.05)
            if start_time_str == '0':
                sched.add_job(job, 'date', args=[req['req_type'], service_id, app_id, input_stream_addr], next_run_time=start_at)
            else:
                start_at = datetime.datetime.strptime(start_time_str, '%Y:%m:%d:%H:%M:%S')

                # If provided start time is past, start now!
                if (start_at - datetime.datetime.now()).total_seconds() < 0:
                    start_at = datetime.datetime.now() + datetime.timedelta(seconds=0.05)

                sched.add_job(job, 'date', args=[req['req_type'], service_id, app_id, input_stream_addr], next_run_time=start_at)

            if req['input_type'] == 'stream':
                duration = req['req_details']['durations'][idx]
                stop_at = start_at + datetime.timedelta(seconds=duration)
                sched.add_job(job, 'date', args=[req['req_type'], service_id, app_id, input_stream_addr, True], next_run_time=stop_at)

            idx += 1
###########


json_data = {

'msg_type': 'scheduleServices',
'request_by': 'deployManager',

'data':{
    'requests':
    [
        {
            'req_type': 'interval_specific',
            'input_type': 'stream',

            'req_details': {
                'num_times': 0,
                'start_timestamp': '0',
                'duration': 3,
                'time_interval': 10,
                'input_stream_addr': 'INDIA/DELHI/SAKET',
                'service_id': 'inception',
                'app_id': 'a-001',
                'model_name': 'inception'
            }
        }
        # ,
        # {
        #     'req_type': 'dependent',
        #     'input_type': 'stream',
        #     'req_details': {
        #         'time_intervals': [2, 2],
        #         'app_ids': ['2', '2', '2'],
        #         'service_ids': ['2', '3', '4'],
        #         'initial_timestamp': '0',
        #         'durations': [2,2,2],
        #         'input_stream_addrs': ['192.168.43.218:1992', '192.168.43.218:1993', '192.168.43.42:1993'],
        #             'model_name': 'inception'
        #     }
        # }
        # ,
        # {
        #     'req_type': 'independent',
        #     'input_type': 'stream',
        #     'req_details': {
        #         'start_timestamps': ['2019:4:1:17:23:00', '2019:4:1:17:22:00'],
        #         'durations': [2, 2],
        #         'app_ids': ['3', '3'],
        #         'service_ids': ['2', '3'],
        #         'input_stream_addrs': ['192.168.43.218:1992', '192.168.43.218:1993'],
        #            'model_name': 'inception'
        #     }
        # }
    ]
}
}

# with open('/home/'+getpass.getuser()+'/scheduler.json') as data:
#     json_data = json.load(data)




jobstores = {
    'mongo': MongoDBJobStore(),
    # 'default': SQLAlchemyJobStore(url='sqlite:///jobs.sqlite')
}
# executors = {
#     'default': ThreadPoolExecutor(20),
#     'processpool': ProcessPoolExecutor(5)
# }
job_defaults = {
    'coalesce': False,
    'max_instances': 5
}


# Start the scheduler
sched = BlockingScheduler()

# jobstore = MyJobStore()
# sched.add_jobstore('my_jobstore', 'mystore')

# def my_listener(event):
#     if event.exception:
#         print('The job crashed :(')
#         print(event)
#
# sched.add_listener(my_listener, EVENT_JOB_ERROR)


def schedule_all(ch, method, props, body):

    json_data = json.loads(body.decode())
    pprint.pprint(json_data)
    if json_data['msg_type'] == 'scheduleServices' and json_data['request_by'] == 'deployManager':
        for request in json_data['data']['requests']:
            # print(request)
            t = threading.Thread(target=schedule_job, args=(request,))
            t.deamon = True
            t.start()

    sched.start()



ip_channel.basic_consume(on_message_callback=schedule_all, queue=ip_queue_name)
ip_channel.start_consuming()

############################### TESTING ###################################
# pprint.pprint(json_data)
# if json_data['msg_type'] == 'scheduleServices' and json_data['request_by'] == 'deployManager':
#     for request in json_data['data']['requests']:
#         # print(request)
#         t = threading.Thread(target=schedule_job, args=(request,))
#         t.deamon = True
#         t.start()
###########################################################################

sched.start()
