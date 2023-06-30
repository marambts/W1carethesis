# ************************
import math
import time
import asyncio
import adafruit_wave as wave
from ulab import numpy as np
import iir_filter
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
        self.buffer = []
        self.weighted = []
        # Sum of squares of weighted mic samples
        self.sum_sqr_weighted = []
        #Accumulated Noise Power
        self.Leq_sum_sqr = 0
        #Samples Counter
        self.Leq_samples = 0
        

q = sum_queue_t()
weight = sum_queue_t()
#............Sampling Initialization..............
SAMPLE_RATE = 44100 #Hz
SAMPLE_BITS = 16 #BITS
SAMPLES_SHORT = SAMPLE_RATE//10  #~100ms                                                     
SAMPLES_LEQ = (SAMPLE_RATE*LEQ_PERIOD)                                                    
                                                                                                    
#initialize laeq value
nRF52840_LAeq = 0

# How often we are going to poll the sensor (If you change this, you need
# to change the filter above and the integration time below)
dt = 100000000 #100ms

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
                

#......................Initialize Filters...................................
equalize = iir_filter.IIR_filter(sos_inmp)
aweight = iir_filter.IIR_filter(sos_a)

#......extraction of samples from wav file.............

with wave.open('recording_1s.wav')as w: #kaya 1 second, di kaya 6 seconds
    #Get the audio file parameters
    sample_width = w.getsampwidth()
    num_frames = w.getnframes()
    #print(w.getframerate())
    #Read all frames from the WAV file
    audio_data = w.readframes(num_frames)
    

async def Laeq_computation():
    global audio_data #type: bytes
    index = 0
    
    while q.Leq_samples < len(range(SAMPLE_RATE)):
        q.buffer = audio_data[index:index+SAMPLES_SHORT] #[0:4410] len = 4411 , type: bytes

        q.Leq_sum_sqr += sum(q.buffer) #type: int
        q.Leq_samples += SAMPLES_SHORT #type: int
        print(q.Leq_sum_sqr, q.Leq_samples)
    
    if q.Leq_samples >= SAMPLE_RATE * LEQ_PERIOD:
            #print(q.Leq_sum_sqr)
        Leq_RMS = math.sqrt(q.Leq_sum_sqr / q.Leq_samples)
            #print(MIC_OFFSET_DB, MIC_REF_DB, Leq_RMS, MIC_REF_AMPL)
        nRF52840_LAeq = MIC_OFFSET_DB + MIC_REF_DB + 20 * math.log(Leq_RMS / MIC_REF_AMPL, 10)
        q.Leq_sum_sqr = 0
        q.Leq_samples = 0

        print("{:.1f} dBA".format(nRF52840_LAeq))

#async def mfcc():

#.........mfcc code here.......................
    

async def main():
    laeq_compute = asyncio.create_task(Laeq_computation())
    #mfcc_compute = asyncio.create_task()

    while True:
        await asyncio.sleep_ms(10)
        break #remove this during continuous testing
            
    

asyncio.run(main())