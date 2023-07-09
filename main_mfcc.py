#...........mfcc configuration...............
import machine
import math
import struct
import array
from machine import I2S, Pin

#.......wifi initialization
import micropython
import network

# ............I2S sensor initializations.............
from machine import I2S
from machine import Pin
from machine import UART

#..........MQTT Initialization.............
import time
import json
import ubinascii
import machine
from umqtt.simple import MQTTClient
import ussl

#............syncing...................
import usocket
import ujson

# Configuration parameters
SAMPLE_RATE = 44100  # Sample rate of the audio input
FRAME_SIZE = 512  # Size of each audio frame
NUM_CEPSTRUM = 13  # Number of MFCC coefficients to calculate
NUM_FILTERS = 26  # Number of Mel filters to use
LOWER_FREQUENCY = 0  # Lower frequency limit for Mel filters
UPPER_FREQUENCY = 22050  # Upper frequency limit for Mel filters

# Pre-compute Mel filterbank
def compute_mel_filterbank(sample_rate):
    filterbank = []
    mel_points = []
    lower_mel = hz_to_mel(LOWER_FREQUENCY)
    upper_mel = hz_to_mel(UPPER_FREQUENCY)
    mel_range = upper_mel - lower_mel

    # Compute equally spaced points along the Mel scale
    for i in range(NUM_FILTERS + 2):
        mel_points.append(lower_mel + (i * mel_range) / (NUM_FILTERS + 1))

    # Convert Mel points back to Hz scale
    hz_points = [mel_to_hz(mel) for mel in mel_points]

    for i in range(1, NUM_FILTERS + 1):
        filterbank.append([0] * (FRAME_SIZE // 2 + 1))
        for j in range(FRAME_SIZE // 2 + 1):
            if hz_points[i - 1] <= j * sample_rate / FRAME_SIZE <= hz_points[i]:
                filterbank[i - 1][j] = (
                    (j * sample_rate / FRAME_SIZE - hz_points[i - 1])
                    / (hz_points[i] - hz_points[i - 1])
                )
            elif hz_points[i] <= j * sample_rate / FRAME_SIZE <= hz_points[i + 1]:
                filterbank[i - 1][j] = (
                    (hz_points[i + 1] - j * sample_rate / FRAME_SIZE)
                    / (hz_points[i + 1] - hz_points[i])
                )

    return filterbank

# Convert frequency to Mel scale
def hz_to_mel(frequency):
    return 2595 * math.log10(1 + frequency / 700)

# Convert Mel scale to frequency
def mel_to_hz(mel):
    return 700 * (10 ** (mel / 2595) - 1)

# Calculate MFCC coefficients
def compute_mfcc(audio_data, sample_rate):
    filterbank = compute_mel_filterbank(sample_rate)
    spectrum = array.array("H", [0] * (FRAME_SIZE // 2 + 1))
    ESP32_MFCC = [0] * NUM_CEPSTRUM

    # Compute magnitude spectrum
    for i in range(FRAME_SIZE // 2 + 1):
        spectrum[i] = abs(audio_data[i])

    # Apply Mel filterbank to spectrum
    mel_spectrum = [0] * NUM_FILTERS
    for i in range(NUM_FILTERS):
        for j in range(FRAME_SIZE // 2 + 1):
            mel_spectrum[i] += spectrum[j] * filterbank[i][j]

    # Compute log Mel spectrum
    log_mel_spectrum = [math.log(mel) if mel > 1e-10 else -10 for mel in mel_spectrum]

    # Instantiate variables with initial values
    for i in range(len(ESP32_MFCC)):
        exec(f"ESP32_MFCC_{i+1} = 0")

    # Assign values from the list to the variables
    for i, value in enumerate(ESP32_MFCC):
        exec(f"ESP32_MFCC_{i+1} = {value}")

import time

class sum_queue_t:
    def __init__(self):
        # raw audio samples
        self.raw_audio = []
        # Sum of squares of weighted mic samples
        self.weighted = []
        # Accumulated Noise Power
        self.Leq_sum_sqr = 0
        # Samples Counter
        self.Leq_samples = 0
        # self.Leq_dB = 0

q = sum_queue_t()

BUFFER_LENGTH_IN_BYTES = 8192
SAMPLE_SIZE_IN_BITS = 16
FORMAT = I2S.MONO
SAMPLE_RATE_IN_HZ = 44100
sample_width = 2
audio_data_int = []
sample_rate = 44100
SAMPLES_SHORT = sample_rate / 8

I2S_WS = 25
I2S_SD = 33
I2S_SCK = 32
I2S_PORT = 0

# initialize buffer size
mic_samples = bytearray(int(SAMPLES_SHORT))
mic_samples_mv = memoryview(mic_samples)


def i2s_callback_rx(arg):
    global mic_samples_mv
    global q
    
    for i in range(len(mic_samples_mv)):
        sample = mic_samples_mv[i]
        shifted_sample = (sample >> 8)//32
        yield shifted_sample

def setup():
    print("Setup I2S ...")
    time.sleep(1)

    global i2s
    i2s = I2S(
        I2S_PORT,
        ws=Pin(I2S_WS),
        sd=Pin(I2S_SD),
        sck=Pin(I2S_SCK),
        mode=I2S.RX,
        bits=SAMPLE_SIZE_IN_BITS,
        format=FORMAT,
        rate=SAMPLE_RATE_IN_HZ,
        ibuf=BUFFER_LENGTH_IN_BYTES,
    )
    time.sleep_ms(10)

    i2s.irq(i2s_callback_rx)
    num_read = i2s.readinto(mic_samples_mv)
    time.sleep_ms(10)

def loop():
    sample = bytearray(2)
    bytes_read = i2s.readinto(sample)
    if bytes_read > 0:
        value = struct.unpack("<h", sample)[0]
        time.sleep(0.0005)
        #print(value)
        
setup()

    # Process audio samples
audio_samp = 0

while audio_samp != sample_rate:
    audio_samp += 1
    loop()

def main():
    # Setup I2S
                           
    # Read audio samples from I2S
    num_read = i2s.readinto(mic_samples_mv)

    # Convert audio samples to list of integers
    audio_data = [sample for sample in mic_samples]

    # Compute MFCC
    ESP32_MFCC = compute_mfcc(audio_data, SAMPLE_RATE)

        # Print MFCC coefficients
    print(ESP32_MFCC)            
    
#.........Send dB(A) reading via MQTT.............

def iso():
    # Convert seconds to a tuple representing local time
    local_time = time.localtime(time.time())

    # Format the local time in ISO 8601 format
    formatted_time = "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}".format(
        local_time[0],
        local_time[1],
        local_time[2],
        local_time[3],
        local_time[4],
        local_time[5]
    )
    return formatted_time
    
class MQTT_client:
    def __init__(self):
        try:
            print("Connecting to MQTT...")
            self.client = MQTTClient(client_id = ubinascii.hexlify(machine.unique_id()),
                server = BROKER_URL,
                user = USER,
                password = PASSWORD,
                ssl = True,
                keepalive = 60,
                ssl_params = {
                    'key' : None,
                    'server_side' : False,
                    'server_hostname' : BROKER_URL
                })

            self.client.connect()
            print("Successfully connected to MQTT")
            
        except OSError as e:
            print(e)
            print("Connect unsuccessful. Rebooting.")
            time.sleep(10)
            machine.reset()
        
            
        self.topic = b'jsontest/ECE199_NOISE_MONITORING'
    
    def make_message_mfcc(self,node_ID, ESP32_MFCC_1, ESP32_MFCC_2, ESP32_MFCC_3, ESP32_MFCC_4, ESP32_MFCC_5, ESP32_MFCC_6, ESP32_MFCC_7, ESP32_MFCC_8, ESP32_MFCC_9, ESP32_MFCC_10, ESP32_MFCC_11, ESP32_MFCC_12, ESP32_MFCC_13):
        out_msg = {}
        out_msg['type'] = "data"
        out_msg['source'] = node_ID
        out_msg['local_time'] =  iso() #datetime.datetime.now(timezone.utc).isoformat() #time.localtime()
        out_msg['ESP32_MFCC_1'] = float(ESP32_MFCC_1)
        out_msg['ESP32_MFCC_2'] = float(ESP32_MFCC_2)
        out_msg['ESP32_MFCC_3'] = float(ESP32_MFCC_3)
        out_msg['ESP32_MFCC_4'] = float(ESP32_MFCC_4)
        out_msg['ESP32_MFCC_5'] = float(ESP32_MFCC_5)
        out_msg['ESP32_MFCC_6'] = float(ESP32_MFCC_6)
        out_msg['ESP32_MFCC_7'] = float(ESP32_MFCC_7)
        out_msg['ESP32_MFCC_8'] = float(ESP32_MFCC_8)
        out_msg['ESP32_MFCC_9'] = float(ESP32_MFCC_9)
        out_msg['ESP32_MFCC_10'] = float(ESP32_MFCC_10)
        out_msg['ESP32_MFCC_11'] = float(ESP32_MFCC_11)
        out_msg['ESP32_MFCC_12'] = float(ESP32_MFCC_12)
        out_msg['ESP32_MFCC_13'] = float(ESP32_MFCC_13)
        
        return json.dumps(out_msg)
    
    def publish(self,msg):
        self.client.publish(self.topic,msg,False,1)
        

def sync():
    rtc = machine.RTC()

    # Get current time from system clock
    current_time = time.localtime(time.time())
    print(current_time)

    # Wait for ESP32-M to send the RTC date and time
    client = usocket.socket(usocket.AF_INET, usocket.SOCK_STREAM)
    client.connect(('192.168.84.174', 1234))  # Replace with ESP32-M's IP address
    data = client.recv(1024)
    rtc_datetime = json.loads(data)

    # Set the received date and time on ESP32-S's RTC
    rtc.datetime(tuple(rtc_datetime))

    # Close the connection
    client.close()



#...............connect to wifi............
        
        
sta = network.WLAN(network.STA_IF)
sta.active(True)

ssid = 'momo'
pw = 'momo1515'

# connect to wifi
print("Connecting to ssid " + ssid)
sta.connect(ssid, pw)

while(not sta.isconnected()):
    pass

print("Connected successfully")

#.................main setup................


if __name__ == "__main__":
    
    BROKER_URL = b'ed7632329e6e4fbcbe77b1fa917585a1.s1.eu.hivemq.cloud'
    USER = b'mabutas.m'
    PASSWORD = b'noise196_EEECARE'
    
    sync()
    client = MQTT_client()
    time.sleep(0.001)
    
    while True:
        main()
        staticmfcc = client.make_message_mfcc('Static LAeq', ESP32_MFCC_1, ESP32_MFCC_2, ESP32_MFCC_3, ESP32_MFCC_4, ESP32_MFCC_5, ESP32_MFCC_6, ESP32_MFCC_7, ESP32_MFCC_8, ESP32_MFCC_9, ESP32_MFCC_10, ESP32_MFCC_11, ESP32_MFCC_12, ESP32_MFCC_13)
        client.publish(staticmfcc)
        time.sleep_ms(100)
    
    client.disconnect()

    print("Finished sending all data.") 
    