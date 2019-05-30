from flask import Flask
from flask import Flask, flash, redirect, render_template, request, session, abort
import os
import auth
import json
import time
import urllib2 
import subprocess
import validation
import json
import pymongo
import xmltodict
import sqlite3
import xml_to_json
############################################################

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
myclient = pymongo.MongoClient(mongodb)


database = myclient["metadata"]

service_metadata = database["service_metadata"]

nodes_metadata = database["nodes_metadata"]

sensors_metadata=database["sensors_metadata"]

servers_mapping = database['servers_mapping']







############################################################

app = Flask(__name__)
 
@app.route('/')
def home():
		return render_template('login.html')
 

@app.route('/login', methods=['POST'])
def do_admin_login():

	username=request.form['username']
	password=request.form['password']
	result = auth.authenticate(username, password)
	if result=='valid':
		session['logged_in'] = True	
		return render_template('scheduler_interface.html')
	else:
		return render_template('login.html')
	

@app.route('/admin_login', methods=['POST'])
def do_admin_login_authenticate():

	username=request.form['username']
	password=request.form['password']
	result = auth.authenticate_admin(username, password)
	if result=='valid':
		session['admin'] = True	
		
		config_file=open("/home/mypc/nfs/platform/platform_configs/platform_components.xml","r")
		data=config_file.read()
		config_file.close()

		data=xmltodict.parse(data)



		lb_ip=data['platform']['load_balancer']['ip']
		lb_uname=data['platform']['load_balancer']['uname']

		s_ip=data['platform']['scheduler']['ip']
		s_uname=data['platform']['scheduler']['uname']

		m_ip=data['platform']['monitor']['ip']
		m_uname=data['platform']['monitor']['uname']

		
		return render_template('deploy_platform.html',l_ip=lb_ip,l_uname=lb_uname,s_ip=s_ip,s_uname=s_uname,m_ip=m_ip,m_uname=m_uname)
	else:
		return render_template('admin_login.html')
	
@app.route('/notification_panel.html')
def notification_show():
	return render_template('notification_panel.html')


@app.route('/admin_login.html')
def admin_login_show():
	return render_template('admin_login.html')

@app.route('/counter.html')
def counter_show():
	return render_template('counter.html')



@app.route('/deploy.html')
def deploy_show():
	return render_template('deploy.html')

################################################################


@app.route('/monitor_dashboard.html')
def launch_monitor():
	global service_metadata, nodes_metadata
	new = {}
	query = {'subsystem_type':'server', 'nodeState':'active'}
	new['running_servers'] = nodes_metadata.find(query).count()
	query = {'subsystem_type':'edge', 'nodeState':'active'}
	new['running_edges'] = nodes_metadata.find(query).count()
	query = {'nature_of_service':'flask','service_state':'running'}
	new['flask_services'] = service_metadata.find(query).count()
	query = {'nature_of_service':'tensorflow_serving','service_state':'running'}
	new['tensorflow_services'] = service_metadata.find(query).count()
	query = {'nature_of_service':'system_service','service_state':'running'}
	new['system_services'] = service_metadata.find(query).count()

	query = {'nature_of_service':'flask','service_state':'stopped'}
	fquery = {'nature_of_service':'flask','service_state':'idle'}
	squery = {'nature_of_service':'flask','service_state':'crashed'}

	new['flask_services_i'] = service_metadata.find(query).count()+service_metadata.find(fquery).count()+service_metadata.find(squery).count()
	query = {'nature_of_service':'tensorflow_serving','service_state':'stopped'}
	fquery = {'nature_of_service':'tensorflow_serving','service_state':'idle'}
	squery = {'nature_of_service':'tensorflow_serving','service_state':'crashed'}
	new['tensorflow_services_i'] = service_metadata.find(query).count()+service_metadata.find(fquery).count()+service_metadata.find(squery).count()
	query = {'nature_of_service':'system_service','service_state':'stopped'}
	new['system_services_i'] = service_metadata.find(query).count()

	return render_template('monitor_dashboard.html',new=new)

@app.route('/pages/tables/basic-table.html')
def launch_basic_table():
	global nodes_metadata, servers_mapping
	data=[]
	for x in nodes_metadata.find():
		data.append(x)

	for x in servers_mapping.find():
		servers_data = x['data'].decode().replace("'",'"')
		servers_data = servers_data.replace('False','"false"')
		servers_data = servers_data.replace('True','"true"')
		servers_data = json.loads(servers_data)

	# print (servers_data['1'])
	for server_machines in servers_data['1']:
		print("===============================")
		print(server_machines)
		print("===============================")

	try:
		servers_data['0']
	except:
		servers_data['0']={}

	try:
		servers_data['1']
	except:
		servers_data['1']={}

	for server in servers_data['1']:
		t=servers_data['1'][server]['services_up']
		t=t.split(' ')
		for j in range(len(t)):
			t[j]=t[j].split('$:$')
			try:
				t[j]=t[j][0]+' : '+t[j][1]
			except:
				t[j]=''
		servers_data['1'][server]['services_up']=t
	
	for server in servers_data['0']:
		t=servers_data['0'][server]['services_up']
		t=t.split(' ')
		for j in range(len(t)):
			t[j]=t[j].split('$:$')
			try:
				t[j]=t[j][0]+' : '+t[j][1]
			except:
				t[j]=''
		servers_data['0'][server]['services_up']=t
	

	for server in servers_data['1']:
		t=servers_data['1'][server]['deployed_services']
		t=t.split(' ')
		for j in range(len(t)):
			t[j]=t[j].split('$:$')
			try:
				t[j]=t[j][0]+' : '+t[j][1].split('@#@')[0]
			except:
				t[j]=''
		servers_data['1'][server]['deployed_services']=t

	for server in servers_data['0']:
		t=servers_data['0'][server]['deployed_services']
		t=t.split(' ')
		for j in range(len(t)):
			t[j]=t[j].split('$:$')
			try:
				t[j]=t[j][0]+' : '+t[j][1].split('@#@')[0]
			except:
				t[j]=''
		servers_data['0'][server]['deployed_services']=t



	# {u'1': {u'10.42.0.1': {u'temp_current': 51.5, u'actual_mem_free': 2.9920310974121094, u'isExclusiveServer': False, u'cpu_performance': 8200, u'mem_free': 0.5121858682847449, u'services_up': u'', u'service_count': 3, u'cpu_free': 81.3, u'deployed_services': u'', u'temp_high': 99.0}}}


	# print(servers_data)

	return render_template('/pages/tables/basic-table.html',data=data,server_data=servers_data['1'],edge_data=servers_data['0'])

@app.route('/pages/charts/chartjs.html')
def launch_chart_js():
	global service_metadata
	data=[]
	for x in service_metadata.find():
		new = {}
		node_ips = x['node_ips'].split(' ')
		serving_ips = x['serving_nodes'].split(' ')
		if '' in node_ips:
			node_ips.remove('')
		if '' in serving_ips:
			serving_ips.remove('')
		new['node_ips'] = node_ips
		new['service_id'] = x['service_id']
		new['application_id'] = x['application_id']
		new['replicas_running'] = len(serving_ips)
		new['serving_nodes'] = serving_ips
		new['service_state'] = x['service_state']
		new['nature_of_service'] = x['nature_of_service']
		data.append(new)


	return render_template('/pages/charts/chartjs.html',data=data)


################################################################



@app.route('/sensor_config_input.html')
def sensor_config_show():
	return render_template('sensor_config_input.html')

@app.route('/upload_sensor_file',methods=['POST'])
def sensor_file_upload():
	global sensors_metadata
	application_name=request.form['applicationname']
	
	f = request.files['sensor_file']
	f.save('/home/mypc/nfs/'+application_name+'/'+f.filename)
	
	##################################
	file_name = os.path.expanduser("~/nfs/"+application_name+'/'+f.filename)
	# config_file=open(file_name,"r")
	# data=config_file.read()
	# config_file.close()
	# data=xmltodict.parse(data)
	data=xml_to_json.converttojson(file_name)

	
	for sensor in data:
		
		
		query={'sensor_id': sensor['sensor_id']}
		print query
		if sensors_metadata.find(query).count() == 0:
			sensorEntry = {'sensor_id': sensor['sensor_id'], 'name':sensor['name'], 'type':sensor['type'], 'location':sensor['location'],'stream_ip':'','stream_port':0,'stream_url':'','in_url':''}
			print(sensorEntry)
			x=sensors_metadata.insert_one(sensorEntry)
	
	
  	##################################






	time.sleep(3)



	return "Sensor File Uploaded !"






@app.route('/deploy_files', methods=['POST'])
def upload_files():
	application_name=request.form['applicationname']
	result = auth.validate_app(application_name)
	if result=='invalid':
		return 'Application name already exists. please try again'
	else:
		f = request.files['zip_file']
      	f.save('../applications/'+f.filename)
	
	time.sleep(3)
	
	application_zip_location="../applications/"+application_name+".zip"


	import zipfile
	
	zip_ref = zipfile.ZipFile(application_zip_location, 'r')
	zip_ref.extractall("../applications/")

	ans1,ans2=validation.check_directory_structure("../applications/"+application_name,"../directory_structure")
	# os.system("rm -r ../applications/"+application_name)
	# os.system("rm -r /home/mypc/nfs/"+application_name)
	print ans1
	print ans2
	if(ans1=="no"):
		#ans2=ans2.split("../applications")[1]
		return render_template("application_not_deployed.html",ans2=ans2)	
	
	zip_ref.extractall("/home/mypc/nfs/")
	zip_ref.close()
	os.system("python3 ../deployManagerCode.py "+application_name)
	# f=open("dmc_logs","rb")
	# data=f.read()
	# f.close()
	return render_template("application_deployed.html")



@app.route('/schedule_job', methods=['POST'])
def schedule_job():
	req_type=request.form['type']
	
	service_id=request.form['service_id']
	app_id=request.form['app_id']
	run_dependent=request.form['run_dependent']
	num_times=request.form['num_times']
	start_timestamp=request.form['start_timestamp']
	duration=request.form['duration']
	time_interval=request.form['time_interval']

	str_param=req_type+"^%^"+service_id+"^%^"+app_id+"^%^"+num_times+"^%^"+start_timestamp+"^%^"+duration+"^%^"+time_interval+"^%^"+run_dependent
	os.system("python2 ../schedule_job.py "+str_param)
	
	return render_template("application_scheduled.html")

@app.route("/logout")
def logout():
	session['logged_in'] = False
	session['admin']= False
	return render_template('login.html')


@app.route("/deploy_the_platform",methods=['POST'])
def deploy_the_platform():
	os.system("python3 ../launch_platform.py")
	return render_template('platform_deployed.html')

@app.route("/add_notification_emails",methods=['POST'])
def update_emails():
	service=request.form['service']
	emails=request.form['email']


	
	try:
		with sqlite3.connect('/home/mypc/Desktop/final_demo/IAS_UI/platform_database.db') as con:
			
			cur=con.cursor()
			cur.execute("INSERT INTO notification_details values ('"+service+"','"+emails+"')")
			print "here"
	except Exception as e:
		print e

	return render_template('platform_deployed.html')



@app.route('/foo', methods=['POST']) 
def foo():
    if not request.json:
        abort(400)
    print request.json
    return json.dumps(request.json)


 
if __name__ == "__main__":
	app.secret_key = os.urandom(12)
	app.run(debug=True,host='0.0.0.0', port=9669)