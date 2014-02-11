#!/usr/bin/python

# Function to send image packets 
def send_image(data):
    NTX2 = serial.Serial(
        "/dev/ttyAMA0",
        600,
        serial.EIGHTBITS,
        serial.PARITY_NONE,
        serial.STOPBITS_TWO
    )
    NTX2.write(data)
    NTX2.close()

os.system("raspistill -o -q 50 -h 320 -w 480 img.jpg")
os.system("ssdv img.jpg img.txt")

with open("img.txt", "r") as f:
	string = f.read()
	splits = [string[x:x+8] for x in range(0,len(string),8)]

print(splits)