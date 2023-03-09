# ************************
#
import machine
import time
import math
import utime

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

#Initializing an I2S microphone for Sampling

SAMPLE_RATE = 48000  # Hz, fixed to design of IIR filters
SAMPLE_BITS = 32    # bits
SAMPLE_T = int       #MicroPython does not have int32_t, not sure if this is the proper alternative
SAMPLES_SHORT = int(SAMPLE_RATE/8)  # ~125ms
LEQ_PERIOD = 1 #seconds (s)
SAMPLES_LEQ = SAMPLE_RATE * LEQ_PERIOD
DMA_BANK_SIZE = SAMPLES_SHORT / 16
DMA_BANKS = 32

# Data we push to 'samples_queue'

class sum_queue_t:
    def __init__(self):
        # Sum of squares of mic samples, after Equalizer filter
        self.sum_sqr_SPL = 0.0
        # Sum of squares of weighted mic samples
        self.sum_sqr_weighted = 0.0
        # Debug only, FreeRTOS ticks we spent processing the I2S data
        self.proc_ticks = 0

samples_queue = []
 
# Static buffer for block of samples

import array

samples = array.array('f', [0.0] * SAMPLES_SHORT)

# I2S Microphone sampling setup 

def mic_i2s_init():
    i2s_config = {
        "mode": (I2S_MODE_MASTER | I2S_MODE_RX),
        "sample_rate": SAMPLE_RATE,
        "bits_per_sample": SAMPLE_BITS,
        "channel_format": I2S_CHANNEL_FMT_ONLY_LEFT,
        "communication_format": (I2S_COMM_FORMAT_I2S | I2S_COMM_FORMAT_I2S_MSB),
        "intr_alloc_flags": ESP_INTR_FLAG_LEVEL1,
        "dma_buf_count": DMA_BANKS,
        "dma_buf_len": DMA_BANK_SIZE,
        "use_apll": True,
        "tx_desc_auto_clear": False,
        "fixed_mclk": 0
    }
    # I2S pin mapping
    pin_config = {
        "bck_io_num": I2S_SCK,
        "ws_io_num": I2S_WS,
        "data_out_num": None,
        "data_in_num": I2S_SD
    }

    i2s_driver_install(I2S_PORT, i2s_config, 0, None)


    i2s_set_pin(I2S_PORT, pin_config)
    
#I2S Reader Task
#FreeRTOS priority and stack size in 32 bit words)

I2S_TASK_PRI = 4
I2S_TASK_STACK = 2048

I2S_TASK_PRI = 4
I2S_TASK_STACK = 2048

def mic_i2s_reader_task(parameter):
    mic_i2s_init()

    # Discard first block, microphone may have startup time (i.e. INMP441 up to 83ms)
    bytes_read = 0
    i2s_read(I2S_PORT, samples, SAMPLES_SHORT * 4, bytes_read, portMAX_DELAY)

    while True:
        # Block and wait for microphone values from I2S
        #
        # Data is moved from DMA buffers to our 'samples' buffer by the driver ISR
        # and when there is requested ammount of data, task is unblocked
        #
        # Note: i2s_read does not care it is writing in float[] buffer, it will write
        #       integer values to the given address, as received from the hardware peripheral. 
        i2s_read(I2S_PORT, samples, SAMPLES_SHORT * 4, bytes_read, portMAX_DELAY)

        start_tick = ticks_ms()

        # Convert (including shifting) integer microphone values to floats, 
        # using the same buffer (assumed sample size is same as size of float), 
        # to save a bit of memory
        int_samples = bytearray(samples)
        for i in range(0, SAMPLES_SHORT):
            int_samples[i * 4: (i + 1) * 4] = struct.pack("<i", MIC_CONVERT(struct.unpack("<i", int_samples[i * 4: (i + 1) * 4])[0]))
        samples = bytearray(int_samples)

        q = {}
        # Apply equalization and calculate Z-weighted sum of squares, 
        # writes filtered samples back to the same buffer.
        q['sum_sqr_SPL'] = MIC_EQUALIZER.filter(samples, samples, SAMPLES_SHORT)

        # Apply weighting and calucate weigthed sum of squares
        q['sum_sqr_weighted'] = WEIGHTING.filter(samples, samples, SAMPLES_SHORT)

        # Debug only. Ticks we spent filtering and summing block of I2S data
        q['proc_ticks'] = ticks_ms() - start_tick

        # Send the sums to FreeRTOS queue where main task will pick them up
        # and further calcualte decibel values (division, logarithms, etc...)
        xQueueSend(samples_queue, q, portMAX_DELAY)


# Setup and main loop
#
# Note: Use doubles, not floats, here unless you want to pin
#       the task to whichever core it happens to run on at the moment

# If needed, now you can actually lower the CPU frequency,
# i.e. if you want to (slightly) reduce ESP32 power consumption
machine.freq(80000000)  # It should run as low as 80MHz

samples_queue = _thread.allocate_lock()

# Create the I2S reader task
def mic_i2s_reader_task(samples_queue):
    i2s = I2S(0)
    i2s.readinto(samples_queue)

# Create the I2S reader thread
_thread.start_new_thread(mic_i2s_reader_task, (samples_queue,))

# Initialize variables
Leq_samples = 0
Leq_sum_sqr = 0
Leq_dB = 0

while True:
    # Wait for new samples
    q = samples_queue.get()

    # Calculate dB values relative to MIC_REF_AMPL and adjust for microphone reference
    short_RMS = math.sqrt(q['sum_sqr_SPL'] / SAMPLES_SHORT)
    short_SPL_dB = MIC_OFFSET_DB + MIC_REF_DB + 20 * math.log10(short_RMS / MIC_REF_AMPL)

    # In case of acoustic overload or below noise floor measurement, report infinity Leq value
    if short_SPL_dB > MIC_OVERLOAD_DB:
        Leq_sum_sqr = float('inf')
    elif math.isnan(short_SPL_dB) or (short_SPL_dB < MIC_NOISE_DB):
        Leq_sum_sqr = float('-inf')

    # Accumulate Leq sum
    Leq_sum_sqr += q['sum_sqr_weighted']
    Leq_samples += SAMPLES_SHORT

    # When we gather enough samples, calculate new Leq value
    if Leq_samples >= SAMPLE_RATE * LEQ_PERIOD:
        Leq_RMS = math.sqrt(Leq_sum_sqr / Leq_samples)
        Leq_dB = MIC_OFFSET_DB + MIC_REF_DB + 20 * math.log10(Leq_RMS / MIC_REF_AMPL)
        Leq_sum_sqr = 0
        Leq_samples = 0
        
        print("%.1f dBA" % Leq_dB)
        
    utime.sleep(0.01)  # Wait for 10ms

