import xmltodict
import sys
import json

def converttojson(xmlfile):
	# xmlfile = sys.argv[1]

	datasource = open(xmlfile)
	o = xmltodict.parse(datasource)
	data = json.dumps(o)

	
	data = json.loads(data)

	# print(data)

	sensors_available = data["sensors"]["sensor"]

	# print(sensors_available)

	result = []
	final_result = {}

	# f = open(sys.argv[2], "w")

	for sensor in sensors_available:
		data = {}
		data["name"] = sensor["name"].encode("ascii","replace")
		data["type"] = sensor["type"].encode("ascii","replace")
		data["sensor_id"] = sensor["sensor_id"].encode("ascii","replace")
		data["location"] = sensor["location"].encode("ascii","replace")
		result.append(data)
	final_result["data"] = result
	return result


