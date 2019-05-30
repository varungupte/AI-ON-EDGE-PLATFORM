import requests
from REQHandler import ReqHandler

REQ = ReqHandler()

counter_service_add = REQ.call(call_type = 'rest_call', call_to = 'server/edge',
                      application_id = 'submarine_exploration', service_id = 'counter_service',
                      parameters = [10]).decode()

counter_service_add = counter_service_add.replace("'",'"')
counter_service_add = json.loads(counter_service_add)
counter_service_add = counter_service_add['rest_url'].split('/')[0]

requests.get(url='http://'+counter_service_add+'/inc')
