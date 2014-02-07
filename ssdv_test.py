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
os.system("ssdv ******************************")

