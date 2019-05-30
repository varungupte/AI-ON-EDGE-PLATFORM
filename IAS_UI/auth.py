import sqlite3

def authenticate(username, password):
	try:
		with sqlite3.connect('/home/mypc/Desktop/docker/IAS_UI/platform_database.db') as con:
			
			cur=con.cursor()

			credentials = (username, password)
			print credentials
			cur.execute("SELECT * FROM user_details WHERE username = ? and password = ?", credentials)
			print "here"			
			result = cur.fetchone()
			if result is None:
				return "invalid"
			else:
				return "valid"

	except Exception as e:
		print e


def authenticate_admin(username, password):
	try:
		with sqlite3.connect('/home/mypc/Desktop/docker/IAS_UI/platform_database.db') as con:
			
			cur=con.cursor()

			credentials = (username, password)
			print credentials
			cur.execute("SELECT * FROM admin_details WHERE username = ? and password = ?", credentials)
			print "here"			
			result = cur.fetchone()
			if result is None:
				return "invalid"
			else:
				return "valid"

	except Exception as e:
		print e




def validate_app(application_name):
	try:
		with sqlite3.connect('/home/mypc/Desktop/docker/IAS_UI/platform_database.db') as con:
			cur=con.cursor()
			credentials = (application_name)
			print credentials
			cur.execute("SELECT * FROM application_details WHERE applicationname ='"+application_name+"'")
			result = cur.fetchone()
			if result is None:
				return "valid"
			else:
				return "invalid"

	except Exception as e:
		print e
	
	
