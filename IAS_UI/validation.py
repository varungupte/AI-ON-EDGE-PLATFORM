import os
from os import listdir
from os.path import isfile, join, exists
import xmltodict, json

# app_path = "/home/anurag/Desktop/IAS/XML/app01"

# def check_sensor(app_path):
# 	flag = "yes"
# 	app_config_path = "application.config"
# 	services_config_path = "app/service.config"

# 	datasource = open(join(app_path, app_config_path))
# 	o = xmltodict.parse(datasource)
# 	data = json.dumps(o)
# 	data = json.loads(data)



# 	sensors_available = data["application"]["sensors_installed"]
# 	sensors_available = sensors_available["sensor"]
# 	sensors_avail=[]
# 	if type(sensors_available) != list:
# 		sensors_avail.append(sensors_available)
# 		sensors_available=sensors_avail

# 	sensors_avail_dict = {}
# 	#print sensors_available
# 	for sensor in sensors_available:
# 		sensors_avail_dict[sensor["sensor_name"]] = sensor

# 	sensors_available = sensors_avail_dict

# 	files = listdir(join(app_path,services_config_path))

# 	for file in files:
# 		datasource = open(app_path + "/" + services_config_path + "/" + file)
# 		o = xmltodict.parse(datasource)
# 		data = json.dumps(o)
# 		data = json.loads(data)
# 		sensors_required = data["service"]["sensors_required"]
# 		sensors_required = sensors_required["sensor"]
		
# 		for sensor in sensors_required:
# 			if sensor["sensor_name"] not in sensors_available:
# 				print("error in :")
# 				print(file)
# 				print(sensor["sensor_name"])
# 				flag = "no"
# 			else:
# 				#print("correct")
# 				#print(sensor["sensor_name"])
# 				s = sensors_available[sensor["sensor_name"]]
# 				if s != sensor:
# 					print("error in :")
# 					print(file)
# 					print(sensor["sensor_name"])
# 					flag = "no"

# 			#print("")

# 	return flag

def check_directory_structure(app_path, directory_structure):

	flag = "yes"
	comment = ""

	print("")
	print("Checking directory structure...")
	print("")

	with open(directory_structure) as f:
		try:
			for line in f:
				if line[len(line)-1] == "\n":
					line = line[:-1]
				line = line.split(":")
				file_type = line[0]
				path = line[1]
				if file_type == "d":
					if os.path.isdir(join(app_path, path)) == False:
						flag = "no"
						print("Directory structure is not correct.")
						print("")
						comment = "Error : Directory " + join(app_path,path) + " not found."
						print(comment)
						print("")
						break
				if file_type == "f":
					if os.path.isfile(join(app_path, path)) == False:
						flag = "no"
						print("Directory structure is not correct.")
						print("")
						comment = "Error : File " + join(app_path,path) + " not found."
						print(comment)
						print("")
					
		except:
			print("Platform should provide a directory structure.")
			print("Directory ")
			flag = "no"

	if flag == "yes":
		print("Directory structure is correct.")
		comment = "OK"
		print("")

	return flag, comment

# print(check_directory_structure(app_path, "../directory_structure"))
