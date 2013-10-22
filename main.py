#!/usr/bin/python

import os
import glob
import subprocess
import serial
import time
import crcmod
from Adafruit_BMP085 import BMP085

# Setup pressure sensor as bmp
bmp = BMP085(0x77)

# Ready I2C for DS18B20 temperature sensor
os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')
base_dir = '/sys/bus/w1/devices/'
device_folder = glob.glob(base_dir + '28*')[0]
device_file = device_folder + '/w1_slave'

# Functions reads raw temperature data from DS18B20 file
def read_raw_temp():
	catdata = subprocess.Popen(['cat',device_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	out,err = catdata.communicate()
	out_decode = out.decode('utf-8')
	lines = out_decode.split('\n')
	return lines

# Cuts down the raw data string and outputs temp in deg C
def read_temp():
	lines = read_raw_temp()
	while lines[0].strip()[-3:] != 'YES':
		time.sleep(0.15)
		lines = read_raw_temp()
	temp_equals = lines[1].find('t=')
	temp_string = lines[1][temp_equals+2:]
	temp = float(temp_string) / 1000.0
	return temp

# Byte array for a UBX command to set Ublox flight mode
setNav = bytearray.fromhex("B5 62 06 24 24 00 FF FF 06 03 00 00 00 00 10 27 00 00 05 00 FA 00 FA 00 64 00 2C 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 16 DC")
# Byte array for UBX command to disable automatic NMEA response from GPS
setNMEA_off = bytearray.fromhex("B5 62 06 00 14 00 01 00 00 00 D0 08 00 00 80 25 00 00 07 00 01 00 00 00 00 00 A0 A9")

# Function to disable all NMEA sentences
def disable_sentences():
	
	# Open serial connection to write to GPS
	GPS = serial.Serial('/dev/ttyAMA0', 9600, timeout=1)
 
	# Disabling all NMEA sentences
	GPS.write("$PUBX,40,GLL,0,0,0,0*5C\r\n")
	GPS.write("$PUBX,40,GSA,0,0,0,0*4E\r\n")
	GPS.write("$PUBX,40,RMC,0,0,0,0*47\r\n")
	GPS.write("$PUBX,40,GSV,0,0,0,0*59\r\n")
	GPS.write("$PUBX,40,VTG,0,0,0,0*5E\r\n")
	GPS.write("$PUBX,40,GGA,0,0,0,0*5A\r\n")
	
	# Close serial connection
	GPS.close()
 
# Function to send commands to the GPS
def sendUBX(MSG, length):
	
	print("Sending UBX Command...")
	ubxcmds = ""

	for i in range(length):
		# Write each byte of the UBX command to the serial port
		GPS.write(chr(MSG[i]))
		# Build up sent message debug output string
		ubxcmds = ubxcmds + str(MSG[i]) + " "

	# Send new line to GPS module
	GPS.write("\r\n")
	# Print UBX command (debugging)
	print(ubxcmds)
	print("UBX Command Sent!")

# Function for CRC-CCITT checksum
crc16f = crcmod.predefined.mkCrcFun('crc-ccitt-false')
disable_sentences()

# Counter will increase as sentence ID
counter = 0
 
# Function to send telemtry and packets
def send(data):
	# Open serial @ 50 baud for transmission with 8 character bits, no parity and two stop bits
	NTX2 = serial.Serial('/dev/ttyAMA0', 50, serial.EIGHTBITS, serial.PARITY_NONE, serial.STOPBITS_TWO)
	# Write final datastring to the serial port
	NTX2.write(data)
	# Print data (debugging)
	# print(data)
	# Close serial port
	NTX2.close()
	
# Function reads GPS and processes returned data ready for transmission
def read_data():

	callsign = "HENHAB"
	satellites = 0
	lats = 0
	northsouth = 0
	lngs = 0
	westeast = 0
	altitude = 0
	time = 0
	latitude = 0
	longitude = 0
	
	global counter
	# Open GPS serial connection
	gps = serial.Serial('/dev/ttyAMA0', 9600, timeout=1)
	# Request a PUBX sentence
	gps.write("$PUBX,00*33\n")
	# Read GPS
	NMEA_sentence = gps.readline()
	
	print("GPS sentence read!")
	# While we don't have a sentence
	if NMEA_sentence.startswith("$PUBX"):
		#gps.write("$PUBX,00*33\n")
		#NMEA_sentence = gps.readline() # re-read ready for re-looping
		#print "Still Bad Sentence"
	 
		gps.close()
 
		print(NMEA_sentence)

		# Split sentence into individual fields
		data = NMEA_sentence.split(",")
 
		# If it does start with a valid sentence but with no fix
		if data[18] == "0":
			print("No Lock")
			pass
		
		# If it does start with a valid sentence and has a fix
		else:
			# Parsing required telemetry fields
			satellites = data[18]
			lats = data[3]
			northsouth = data[4]
			lngs = data[5]
			westeast = data[6]
			alt_gps = int(float(data[7]))

			time = float(data[2])

			# Create a string out of time (format ensures 0 is included at start)
			string = "%06i" % time
			hours = string[0:2]
			minutes = string[2:4]
			seconds = string[4:6]
			# Final time string as 'HH:MM:SS'
			time = str(str(hours) + ':' + str(minutes) + ':' + str(seconds))
		
			latitude = convert(lats, northsouth)
			longitude = convert(lngs, westeast)

			temp_external = read_temp()

			temp_internal = bmp.readTemperature()
			pressure = bmp.readPressure()
			alt_press = bmp.readAltitude()
		
	# The data string
	string = callsign + ',' + time + ',' + str(counter) + ',' + str(latitude) + ',' + str(longitude) + ',' + satellites + ',' + str(alt_gps) + ',' + str(alt_press) + ',' str(pressure) + ',' + str(temp_external) + ',' + str(temp_internal)
	# Run the CRC-CCITT checksum
	csum = str(hex(crc16f(string))).upper()[2:]
	# Create the checksum data
	csum = csum.zfill(4)
	# Append the datastring as per the UKHAS communication protocol
	datastring = str("$$" + string + "*" + csum + "\n")
	# Increment the sentence ID for next transmission
	counter += 1
	print("Sending the following: " + datastring)
	# Send the datastring to the NTX2
	send(datastring)
 
# Function to convert latitude and longitude into a different format
def convert(position_data, orientation):

		decs = ""
		decs2 = ""

		for i in range(position_data.index('.') - 2):
			decs = decs + position_data[i]

		for i in range(position_data.index('.') - 2, len(position_data) - 1):
			decs2 = decs2 + position_data[i]

		position = float(decs) + float(str((float(decs2)/60))[:8])
		
		if orientation == ("S") or orientation == ("W"):
			position = 0 - position
		
		return position

while True:
	
	# Open serial connection to GPS
	GPS = serial.Serial('/dev/ttyAMA0', 9600, timeout=1)
	print("Serial connection opened")

	# Wait for bytes to be physically read from GPS
	GPS.flush()
	
	# Send command to enable flight mode
	sendUBX(setNav, len(setNav))
	print("sendUBX_ACK function complete")

	# Turn off NMEA sentences
	sendUBX(setNMEA_off, len(setNMEA_off))
	
	GPS.flush()

	GPS.close()
	print("Serial connection closed")
	
	# Run the read_data function to get the data and parse with status of flightmode
	read_data()
