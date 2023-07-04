# ************************
import machine
import math
import utime as time
import array


gc.enable()

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
        # raw audio samples
        self.raw_audio = []
        # Sum of squares of weighted mic samples
        self.weighted = []
        #Accumulated Noise Power
        self.Leq_sum_sqr = 0
        #Samples Counter
        self.Leq_samples = 0
        #self.Leq_dB = 0

q = sum_queue_t()

#............Sampling Initialization..............
SAMPLE_RATE = 44100 #Hz
SAMPLE_BITS = 32 #BITS
SAMPLES_SHORT = SAMPLE_RATE/10                                                      
SAMPLES_LEQ = (SAMPLE_RATE*LEQ_PERIOD)                                                    
                                                      
#................I2S pin mapping..................
sck_pin = 32   # Serial clock output
ws_pin = 25    # Word clock output
sd_pin = 33   # Serial data output
I2S_ID = 0                                                   

#.................audio configuration...................
BUFFER_LENGTH_IN_BYTES = 8192
SAMPLE_SIZE_IN_BITS = 32
FORMAT = I2S.MONO
SAMPLE_RATE_IN_HZ = 44100


#.......................IIR Coefficients..................................
#Once implemented, remember to recheck coefficients for Fs = 44.1kHz.
#Recheck-able with MATLAB pwede pa i-tweak ang coefficients
#Note that that the IIR_Filter module takes in SOS coefficients expressed as an n number of 1 x 6 matrices.

#KOTOSKI Equalizer
#SOS_IIR_Filter INMP441 = {
#gain: 1.00197834654696, 
sos_inmp = [[1.0000,   -1.9952,    0.9952,    1.0000,   -1.9869,    0.9870]]


#KOTOSKI A weighting filter IIR Second Order Sections
# B = [0.169994948147430, 0.280415310498794, -1.120574766348363, 0.131562559965936, 0.974153561246036, -0.282740857326553, -0.152810756202003]
# A = [1.0, -2.12979364760736134, 0.42996125885751674, 1.62132698199721426, -0.96669962900852902, 0.00121015844426781, 0.04400300696788968]
#gain: 0.169994948147430
sos_a = [[1.0000, 3.7584,  1.0081, 1.0000,   -0.1132,   -0.0565],
    [1.0000,   -0.1086,   -0.8914,    1.0000,   -0.0343,   -0.7922],
    [1.0000,   -2.0003,    1.0003,    1.0000,   -1.9822,    0.9823]]

#TEACHMAN - is this for A weighting only or is this cascaded equalizer + A-weighting
#noise = dba.DBA(samples=10000, resolution=dba.B16, 
coeffa= [1.0, -2.3604841 ,  0.83692802,  1.54849677, -0.96903429, -0.25092355,  0.1950274]
coeffb=[0.61367941, -1.22735882, -0.61367941,  2.45471764, -0.61367941, -1.22735882,  0.61367941]
sos_a_teachman =  [[1.0000,    2.0000,    1.0000,    1.0000,    1.1720,    0.3434],
    [1.0000,   -2.0001,    1.0001,    1.0000,   -1.5582,    0.5828],
    [1.0000,   -1.9999,    0.9999,    1.0000,   -1.9743,    0.9744]]

class IIR2_filter:
    """2nd order IIR filter"""
    def __init__(self,s):
        """Instantiates a 2nd order IIR filter
        s -- numerator and denominator coefficients
        """
        self.numerator0 = s[0]
        self.numerator1 = s[1]
        self.numerator2 = s[2]
        self.denominator1 = s[4]
        self.denominator2 = s[5]
        self.buffer1 = 0
        self.buffer2 = 0

    def filter(self,v):
        """Sample by sample filtering
        v -- scalar sample
        returns filtered sample
        """
        input = v - (self.denominator1 * self.buffer1) - (self.denominator2 * self.buffer2)
        output = (self.numerator1 * self.buffer1) + (self.numerator2 * self.buffer2) + input * self.numerator0
        self.buffer2 = self.buffer1
        self.buffer1 = input
        return output
    

class IIR_filter:
    """IIR filter"""
    def __init__(self,sos):
        """Instantiates an IIR filter of any order
        sos -- array of 2nd order IIR filter coefficients
        """
        self.cascade = []
        for s in sos:
            self.cascade.append(IIR2_filter(s))

    def filter(self,v):
        """Sample by sample filtering
        v -- scalar sample
        returns filtered sample
        """
        for f in self.cascade:
            v = f.filter(v)
        return v
    
#......................Initialize Filters...................................
equalize = IIR_filter(sos_inmp)
aweight = IIR_filter(sos_a)


#..............main code here..........................

#initialize buffer size
mic_samples = array.array('i', [0] * 4410)

mic_samples_mv = memoryview(mic_samples)                                              
ESP32_LAeq = 0

def i2s_callback_rx(arg):
    global mic_samples_mv
    global q
    
    for i in range(len(mic_samples_mv)):
        sample = mic_samples_mv[i]
        shifted_sample = (sample >> 8)//32
        yield shifted_sample

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
    global ESP32_LAeq
    
    machine.freq(240000000) # It should run as low as 80MHz, can run up to 240MHZ
    
    start = time.ticks_us()
    iterations = 10 #number of iterations to reach 44.1k samples
    for i in range(iterations):
        start1 = time.ticks_us()
        sampling()
        #for i in range(len(q.raw_audio)):
            #q.weighted = pow(equalize.filter(aweight.filter(q.raw_audio[i])),2)
        #q.Leq_sum_sqr += sum(q.weighted)
        q.Leq_sum_sqr += sum(pow(equalize.filter(aweight.filter(shifted_sample)), 2) for shifted_sample in i2s_callback_rx(None))
        #print(q.sum_sqr_weighted)
        q.Leq_samples += SAMPLES_SHORT
        print(q.Leq_sum_sqr, q.Leq_samples, time.ticks_diff(time.ticks_us(), start1)/1000000)
        
    if q.Leq_samples >= SAMPLE_RATE * LEQ_PERIOD:
        Leq_RMS = math.sqrt(q.Leq_sum_sqr / q.Leq_samples)
        ESP32_LAeq = MIC_OFFSET_DB + MIC_REF_DB + 20 * math.log10(Leq_RMS / MIC_REF_AMPL)
        q.Leq_sum_sqr = 0
        q.Leq_samples = 0

        print("Final LAeq Reading: ", "{:.1f} dBA".format(ESP32_LAeq))
        end = time.ticks_us()
        print("Time for 1-second reading: ", time.ticks_diff(end,start)/1000000, "Seconds")
    
    q.sum_sqr_weighted = []

    gc.collect()
            
    
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
                    #'cert' : open_cert,
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
    
    def make_message_staticlaeq(self,node_ID, ESP32_LAeq):
        out_msg = {}
        out_msg['type'] = "data"
        out_msg['source'] = node_ID
        out_msg['local_time'] =  iso() #datetime.datetime.now(timezone.utc).isoformat() #time.localtime()
        out_msg['ESP32_LAeq'] = ESP32_LAeq
        
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
    
    BROKER_URL = b'ed7632329e6e4fbcbe77b1fa917585a1.s1.eu.hivemq.cloud'
    USER = b'mabutas.m'
    PASSWORD = b'noise196_EEECARE'
    
    # import certs
    #with open('hivemq-com-chain.der') as f:
        #open_cert = f.read()
    
    client = MQTT_client()
    time.sleep(1)
    
    while True:
        laeq_computation()
        staticlaeq = client.make_message_staticlaeq('Static LAeq', ESP32_LAeq)
        client.publish(staticlaeq)
        time.sleep_ms(100)
    
    client.disconnect()

    print("Finished sending all data.") 
    