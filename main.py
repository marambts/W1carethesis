# ************************
#
import machine
import time

# ************************
# Configure the ESP32 wifi
# as Access Point mode.
import network
ssid = 'ESP32-AP-WebServer'
password = '123456789'

ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid=ssid, password=password)
while not ap.active():
    pass
print('network config:', ap.ifconfig())


# ************************
# Configure the socket connection
# over TCP/IP
import socket

# AF_INET - use Internet Protocol v4 addresses
# SOCK_STREAM means that it is a TCP socket.
# SOCK_DGRAM means that it is a UDP socket.
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('',80)) # specifies that the socket is reachable by any address the machine happens to have
s.listen(5)     # max of 5 socket connections


# I2S sensor initializations
import os
from machine import I2S
from machine import Pin\
# ESP32
sck_pin = Pin(2)   # Serial clock output
ws_pin = Pin(15)    # Word clock output
sd_pin = Pin(13)    # Serial data output
I2S_ID = 2

RECORD_TIME_IN_SECONDS = 10
SAMPLE_RATE_IN_HZ = 48000



#======= USER CONFIGURATION =======

WAV_SAMPLE_SIZE_IN_BITS = 32
WAV_SAMPLE_SIZE_IN_BYTES = WAV_SAMPLE_SIZE_IN_BITS // 8
MIC_SAMPLE_BUFFER_SIZE_IN_BYTES = 4096
SDCARD_SAMPLE_BUFFER_SIZE_IN_BYTES = MIC_SAMPLE_BUFFER_SIZE_IN_BYTES // 2 # why divide by 2? only using 16-bits of 32-bit samples
NUM_SAMPLE_BYTES_TO_WRITE = RECORD_TIME_IN_SECONDS * SAMPLE_RATE_IN_HZ * WAV_SAMPLE_SIZE_IN_BYTES
NUM_SAMPLES_IN_DMA_BUFFER = 320
NUM_CHANNELS = 1

# ************************
# snip_16_mono():  snip 16-bit samples from a 32-bit mono sample stream
# assumption: I2S configuration for mono microphone.  e.g. I2S channelformat = ONLY_LEFT or ONLY_RIGHT
# example snip:
#   samples_in[] =  [0x44, 0x55, 0xAB, 0x77, 0x99, 0xBB, 0x11, 0x22]
#   samples_out[] = [0xAB, 0x77, 0x11, 0x22]
#   notes:
#       samples_in[] arranged in little endian format:
#           0x77 is the most significant byte of the 32-bit sample
#           0x44 is the least significant byte of the 32-bit sample
#
# returns:  number of bytes snipped
def snip_16_mono(samples_in, samples_out):
    num_samples = len(samples_in) // 4
    for i in range(num_samples):
        samples_out[2*i] = samples_in[4*i + 2]
        samples_out[2*i + 1] = samples_in[4*i + 3]

    return num_samples * 2

def create_wav_header(sampleRate, bitsPerSample, num_channels, num_samples):
    datasize = num_samples * num_channels * bitsPerSample // 8
    o = bytes("RIFF",'ascii')                                                   # (4byte) Marks file as RIFF
    o += (datasize + 36).to_bytes(4,'little')                                   # (4byte) File size in bytes excluding this and RIFF marker
    o += bytes("WAVE",'ascii')                                                  # (4byte) File type
    o += bytes("fmt ",'ascii')                                                  # (4byte) Format Chunk Marker
    o += (32).to_bytes(4,'little')                                              # (4byte) Length of above format data
    o += (1).to_bytes(2,'little')                                               # (2byte) Format type (1 - PCM)
    o += (num_channels).to_bytes(2,'little')                                    # (2byte)
    o += (sampleRate).to_bytes(4,'little')                                      # (4byte)
    o += (sampleRate * num_channels * bitsPerSample // 8).to_bytes(4,'little')  # (4byte)
    o += (num_channels * bitsPerSample // 8).to_bytes(2,'little')               # (2byte)
    o += (bitsPerSample).to_bytes(2,'little')                                   # (2byte)
    o += bytes("data",'ascii')                                                  # (4byte) Data Chunk Marker
    o += (datasize).to_bytes(4,'little')                                        # (4byte) Data size in bytes
    return o

# ESP32
sck_pin = Pin(2)   # Serial clock output
ws_pin = Pin(15)    # Word clock output
sd_pin = Pin(13)    # Serial data output
I2S_ID = 2

audio_in = I2S(0,
               sck=sck_pin,
               ws=ws_pin,
               sd=sd_pin,
               mode=I2S.RX,
               bits=32,
               format=I2S.MONO,
               rate=48000,
               ibuf=48000
               )

wav = open('mic_left_channel.wav','wb')


# create header for WAV file and write to SD card
wav_header = create_wav_header(
    SAMPLE_RATE_IN_HZ,
    WAV_SAMPLE_SIZE_IN_BITS,
    NUM_CHANNELS,
    SAMPLE_RATE_IN_HZ * RECORD_TIME_IN_SECONDS
)
num_bytes_written = wav.write(wav_header)

# allocate sample arrays
#   memoryview used to reduce heap allocation in while loop

#6  second buffer
mic_samples = bytearray(6400)
mic_samples_mv = memoryview(mic_samples)

num_sample_bytes_written_to_wav = 0

print('Starting')
# read 32-bit samples from I2S microphone, snip upper 16-bits, write snipped samples to WAV file
while num_sample_bytes_written_to_wav < 192000:
    try:
        num_bytes_read_from_mic = audio_in.readinto(mic_samples_mv)
        if num_bytes_read_from_mic > 0:
            # snip upper 16-bits from each 32-bit microphone sample
            print('%d sample bytes read from i2s' % num_bytes_read_from_mic)
            num_bytes_written = wav.write(mic_samples_mv[:num_bytes_read_from_mic])

            num_sample_bytes_written_to_wav += num_bytes_written
    except (KeyboardInterrupt, Exception) as e:
        print('caught exception {} {}'.format(type(e).__name__, e))
        break


wav.close()

audio_in.deinit()

print('%d sample bytes written to WAV file' % num_sample_bytes_written_to_wav)
print('Done')

# Function for creating the
# web page to be displayed
def web_page():
    
    html_page = """<!DOCTYPE HTML>  
        <html>  
        <head>  
          <meta name="viewport" content="width=device-width, initial-scale=1">  
          <meta http-equiv="refresh" content="1">  
        </head>  
        <body>  
           <center><h2>ESP32 Web Server in MicroPython </h2></center>  
           <center><p>Number of sample bytes written to WAV file : <strong>""" + str(num_sample_bytes_written_to_wav) + """</strong>.</p></center> 
        </body>  
        </html>"""
    return html_page  


while True:
    # Socket accept() 
    conn, addr = s.accept()
    print("Got connection from %s" % str(addr))
    
    # Socket receive()
    request=conn.recv(1024)
    print("")
    print("Content %s" % str(request))

    # Socket send()
    request = str(request)
    
    # Create a socket reply
    response = web_page()
    conn.send('HTTP/1.1 200 OK\n')
    conn.send('Content-Type: text/html\n')
    conn.send('Connection: close\n\n')
    conn.sendall(response)
    
    # Socket close()
    conn.close()

