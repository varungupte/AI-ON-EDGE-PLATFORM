import pika
import uuid
import pickle
import xmltodict
import os
import pymongo

file_name = os.path.expanduser("~/nfs/platform/platform_configs/platform_config.xml")
config_file=open(file_name,"r")
data=config_file.read()
config_file.close()
data=xmltodict.parse(data)
runner_ip=data['platform']['rabbit_server_ip']
mongodb=data['platform']['mongodb']
deploy_manager_ip=data['platform']['deploy_manager_ip']
myclient = pymongo.MongoClient(mongodb)

class ReqClient(object):
    def __init__(self):
        self.connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=runner_ip))
        self.channel = self.connection.channel()
        result = self.channel.queue_declare('', exclusive=True)
        self.callback_queue = result.method.queue

        self.channel.basic_consume(
                queue=self.callback_queue,
                on_message_callback=self.on_response,
                auto_ack=True)

    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = body

    def publish_msg(self, msg):
        self.response = None
        self.corr_id = str(uuid.uuid4())
        self.channel.basic_publish(
                exchange='',
                routing_key='pkmkb',
                properties=pika.BasicProperties(
                        reply_to=self.callback_queue,
                        correlation_id=self.corr_id,
                        ),body=msg)


        while self.response is None:
            self.connection.process_data_events()
        return self.response

class ReqHandler(object):
    def __init__(self):
        self.RpcObject = ReqClient()

    def call(self, call_type = None, call_to = None, application_id = None, service_id = None, parameters = None):
        data = {}
        data['function_name'] = call_type
        data['data'] = {}
        data['data']['call_to'] = call_to
        data['data']['application_id'] = application_id
        data['data']['service_id'] = service_id
        data['data']['function_params'] = parameters
        return self.RpcObject.publish_msg(pickle.dumps(data))
