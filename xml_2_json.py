import xmltodict
import sys
import json

def tojson(filename):
	xmlfile = filename

	datasource = open(xmlfile,"rb")
	o = xmltodict.parse(datasource)
	data = json.dumps(o)

	
	data = json.loads(data)

	
	return json.dumps(data)

# print (tojson('/home/mypc/nfs/services/service.config'))