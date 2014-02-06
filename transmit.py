#!/usr/bin/python
# Code for the "HENHAB" High Altitude Balloon by Henry Plumb (henry@android.net)

import serial
import os
import subprocess
import glob
import time
import shutil
import crcmod
from Adafruit_BMP085 import BMP085

callsign = "HENHAB"
bmp = BMP085(0x77)
counter = 1

# Byte array for a UBX command to set Ublox flight mode
setNav = bytearray.fromhex("B5 62 06 24 24 00 FF FF 06 03 00 00 00 00 10 27 00 00 05 00 FA 00 FA 00 64 00 2C 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 16 DC")
# Byte array for UBX command to disable automatic NMEA response from GPS
setNMEA_off = bytearray.fromhex("B5 62 06 00 14 00 01 00 00 00 D0 08 00 00 80 25 00 00 07 00 01 00 00 00 00 00 A0 A9")

# Function for CRC-CCITT checksum
crc16f = crcmod.predefined.mkCrcFun("crc-ccitt-false")

# Ready I2C connection for DS18B20 temperature sensor
os.system("modprobe w1-gpio")
os.system("modprobe w1-therm")
base_dir = "/sys/bus/w1/devices/"
device_folder = glob.glob(base_dir + "28*")[0]
device_file = device_folder + "/w1_slave"

# Reads raw temp from DS18B20
def read_raw_temp():
    catdata = subprocess.Popen(
        ["cat", device_file],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    out, err = catdata.communicate()
    out_decode = out.decode("utf-8")
    lines = out_decode.split("\n")
    return lines

def read_temp():
    lines = read_raw_temp()
    while lines[0].strip()[-3:] != "YES":
        time.sleep(0.2)
        lines = read_raw_temp()
        equals_pos = lines[1].find("t=")
    if equals_pos != -1:
        temp_ext = float(lines[1][equals_pos + 2:]) / 1000.0
    return temp_ext

# Function to disable all NMEA sentences
def disable_sentences():
    GPS = serial.Serial("/dev/ttyAMA0", 9600, timeout=1)
    GPS.write("$PUBX,40,GLL,0,0,0,0*5C\r\n")
    GPS.write("$PUBX,40,GSA,0,0,0,0*4E\r\n")
    GPS.write("$PUBX,40,RMC,0,0,0,0*47\r\n")
    GPS.write("$PUBX,40,GSV,0,0,0,0*59\r\n")
    GPS.write("$PUBX,40,VTG,0,0,0,0*5E\r\n")
    GPS.write("$PUBX,40,GGA,0,0,0,0*5A\r\n")
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
    print("UBX command sent")

# Function to send telemetry and packets
def send(data):
    NTX2 = serial.Serial(
        "/dev/ttyAMA0",
        50,
        serial.EIGHTBITS,
        serial.PARITY_NONE,
        serial.STOPBITS_TWO
    )
    NTX2.write(data)
    NTX2.close()

# Function to convert latitude and longitude into a different format
def convert(position_data, orientation):
        decs = ""
        decs2 = ""

        for i in range(position_data.index(".") - 2):
            decs = decs + position_data[i]

        for i in range(position_data.index(".") - 2, len(position_data) - 1):
            decs2 = decs2 + position_data[i]

        position = float(decs) + float(str((float(decs2) / 60))[:8])

        if orientation == ("S") or orientation == ("W"):
            position = 0 - position

        return position

# Function reads GPS and processes returned data for transmission
def read_data():
    GPS = serial.Serial("/dev/ttyAMA0", 9600, timeout=1)
    # Request a PUBX sentence
    GPS.write("$PUBX,00*33\n")
    NMEA_sentence = GPS.readline()
    print("GPS sentence read")

    if NMEA_sentence.startswith("$PUBX"):
        GPS.close()
        # Split sentence into individual fields
        data = NMEA_sentence.split(",")

        # If valid but no GPS lock
        if data[18] == "0":
            print("No GPS Lock")
            pass
        # If valid with GPS lock
        else:
            # Parse required data fields
            sats = data[18]
            lats = convert(data[3], northsouth)
            longs = convert(data[5], westeast)
            westeast = data[6]
            alt = int(float(data[7]))

            # Create valid time (start 0 if necessary) and format to "HH:MM:SS"
            string = "%06i" % float(data[2])
            time = str(string[0:2] + ":" + string[2:4] + ":" + string[4:6])

            # Read sensors
            temp_ext = read_temp()
            temp_int = bmp.readTemperature()
            pressure = bmp.readPressure()

    # The telemetry string
    string = ",".join([
        callsign,
        str(counter),
        time,
        str(sats),
        str(lats),
        str(longs),
        str(alt),
        str(pressure),
        str(temp_ext),
        str(temp_int)
    ])
    # Run the CRC-CCITT checksum
    csum = str(hex(crc16f(string))).upper()[2:].zfill(4)
    # Format the string as per the UKHAS protocol
    datastring = str("$$" + string + "*" + csum + "\n")
    # Increment the sentence ID for next transmission
    counter += 1
    print("Sending telemetry string...")
    send(datastring)
    print("Telemetry string sent")

disable_sentences()

while True:

    # Open serial connection to GPS
    GPS = serial.Serial("/dev/ttyAMA0", 9600, timeout=1)
    print("Serial connection opened")

    # Wait for bytes to be physically read from GPS
    GPS.flush()

    # Send command to enable flight mode
    sendUBX(setNav, len(setNav))
    print("sendUBX_ACK function complete - Flight mode enabled")

    # Turn off NMEA sentences
    sendUBX(setNMEA_off, len(setNMEA_off))
    print("NMEA sentences disabled")

    GPS.flush()

    GPS.close()
    print("Serial connection closed")

    read_data()
