# ************************
import machine
import math
import utime as time
import array

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
#from micropython import datetime
import ubinascii
import machine
from umqtt.simple import MQTTClient
import ussl
#from config import BROKER_URL, USER, PASSWORD

#............Configuration..................
LEQ_PERIOD = 1 
#values from microphone datasheet
MIC_OFFSET_DB = 3.0103 #for short_spl_db
MIC_SENSITIVITY = -26 
MIC_REF_DB = 94 #for short_spl_db
MIC_OVERLOAD_DB = 120.0 #dB - Acoustic overload point
MIC_BITS = 24 #mic_ref_ampl
MIC_NOISE_DB = -87 # dB - Noise floor
MIC_REF_AMPL = math.pow(10, (MIC_SENSITIVITY)/20) * ((1<<(MIC_BITS-1)-1)) #for short_spl_db

       
#.............initialization of variables................
class sum_queue_t:
    def __init__(self):
        # Sum of squares of mic samples, after Equalizer filter
        self.sum_sqr_SPL = []
        # Sum of squares of weighted mic samples
        self.sum_sqr_weighted = []
        #Accumulated Noise Power
        self.Leq_sum_sqr = 0
        #Samples Counter
        self.Leq_samples = 0

q = sum_queue_t()

#............Sampling Initialization..............
SAMPLE_RATE = 20000 #Hz
SAMPLE_BITS = 32 #BITS
SAMPLES_SHORT = SAMPLE_RATE/8 #~125ms                                                     
SAMPLES_LEQ = (SAMPLE_RATE*LEQ_PERIOD)                                                    
                                                      
#................I2S pin mapping..................
sck_pin = 32   # Serial clock output
ws_pin = 25    # Word clock output
sd_pin = 33   # Serial data output
I2S_ID = 0                                                   

#.................audio configuration...................
BUFFER_LENGTH_IN_BYTES = 40000
SAMPLE_SIZE_IN_BITS = 16
FORMAT = I2S.MONO
SAMPLE_RATE_IN_HZ = 20000


#..............main code here..........................

#initialize buffer size
mic_samples = bytearray(int(SAMPLES_SHORT))
mic_samples_mv = memoryview(mic_samples)                                              


def i2s_callback_rx(arg):
    global mic_samples_mv
    
    buffer_array = [int(i) for i in mic_samples_mv]
    q.sum_sqr_weighted = buffer_array
    q.sum_sqr_SPL = buffer_array
    #print(q.sum_sqr_weighted)

def sampling():
    global mic_samples_mv
    audio_in = I2S(
        I2S_ID,
        sck=Pin(sck_pin),
        ws=Pin(ws_pin),
        sd=Pin(sd_pin),
        mode=I2S.RX,
        bits=SAMPLE_SIZE_IN_BITS,
        format=FORMAT,
        rate=SAMPLE_RATE_IN_HZ,
        ibuf=BUFFER_LENGTH_IN_BYTES,
        )
    time.sleep_ms(100)
        
    audio_in.irq(i2s_callback_rx)
    num_read = audio_in.readinto(mic_samples_mv)
    time.sleep_ms(100)

def laeq_computation():
    start = time.ticks_us()
    machine.freq(240000000) # It should run as low as 80MHz, can run up to 240MHZ
    #uart = UART(0, 115200)
    

    iterations = 8 #number of iterations to reach 44.1k samples
    for i in range(iterations):
        sampling()
        
        q.Leq_sum_sqr += sum(q.sum_sqr_weighted)
        q.Leq_samples += SAMPLES_SHORT
        print(q.sum_sqr_weighted)
        print(q.Leq_sum_sqr)
        
    if q.Leq_samples >= SAMPLE_RATE * LEQ_PERIOD:
        #print(q.Leq_sum_sqr)
        Leq_RMS = math.sqrt(q.Leq_sum_sqr / q.Leq_samples)
        #print(MIC_OFFSET_DB, MIC_REF_DB, Leq_RMS, MIC_REF_AMPL)
        Leq_dB = MIC_OFFSET_DB + MIC_REF_DB + 20 * math.log10(Leq_RMS / MIC_REF_AMPL)
        q.Leq_sum_sqr = 0
        q.Leq_samples = 0

        print("{:.1f} dBA".format(Leq_dB))
        
    if len(q.sum_sqr_SPL) > SAMPLES_SHORT:
        q.sum_sqr_SPL.pop(0)
    if len(q.sum_sqr_weighted) > SAMPLES_SHORT:
        q.sum_sqr_weighted.pop(0)
            
    
#.........Send dbA reading via MQTT.............

BROKER_URL = b'ed7632329e6e4fbcbe77b1fa917585a1.s1.eu.hivemq.cloud'
USER = b'mabutas.m'
PASSWORD = b'noise196_EEECARE'

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
                    'cert' : cacert_data,
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
            
        self.topic = "jsontest/ECE199_NOISE_MONITORING" #subscribed
        
        
    
    def make_message_staticlaeq(self,node_ID, Leq_dB):
        out_msg = {}
        out_msg['type'] = "data"
        out_msg['source'] = node_ID
        out_msg['local_time'] =  time.localtime() #datetime.now().isoformat()
        out_msg['INMP441_LAeq'] = int()
        
        return json.dumps(out_msg)
        

    def publish(self,msg):
        self.client.publish(self.topic,msg,False,1)

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
    # import certs
    with open('hivemq-com-chain.der') as f:
        cacert_data = f.read()
    
    client = MQTT_client()
    time.sleep(3)
    
    while True:
        laeq_computation()
        time.sleep_ms(100)
        
        staticlaeq = client.make_message_staticlaeq('Static LAeq', Leq_dB) 
        client.publish(staticlaeq)
        time.sleep(1)

    print("Finished sending all data.")        

