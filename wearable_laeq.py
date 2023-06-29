# ************************
import math
import time
import asyncio
import adafruit_wave as wave

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
        # Sum of squares of weighted mic samples
        self.sum_sqr_weighted = []
        #Accumulated Noise Power
        self.Leq_sum_sqr = 0
        #Samples Counter
        self.Leq_samples = 0

q = sum_queue_t()

#............Sampling Initialization..............
SAMPLE_RATE = 44100 #Hz
SAMPLE_BITS = 16 #BITS
SAMPLES_SHORT = SAMPLE_RATE//10 #~125ms                                                     
SAMPLES_LEQ = (SAMPLE_RATE*LEQ_PERIOD)                                                    
                                                                                                    
#initialize laeq value
nRF52840_LAeq = 0
#......extraction of samples from wav file.............

with wave.open('recording_1s.wav')as w: #kaya 1 second, di kaya 6 seconds
    #Get the audio file parameters
    sample_width = w.getsampwidth()
    num_frames = w.getnframes()
    #print(w.getframerate())
    #Read all frames from the WAV file
    audio_data = w.readframes(num_frames)
    

async def Laeq_computation():
    global audio_data
    index = 0
    
    
    while q.Leq_samples < len(range(SAMPLE_RATE)):
        q.sum_sqr_weighted = audio_data[index:index+SAMPLES_SHORT]
        q.Leq_sum_sqr += sum(q.sum_sqr_weighted)
        q.Leq_samples += SAMPLES_SHORT
        print(q.Leq_sum_sqr, q.Leq_samples)
    
    if q.Leq_samples >= SAMPLE_RATE * LEQ_PERIOD:
            #print(q.Leq_sum_sqr)
        Leq_RMS = math.sqrt(q.Leq_sum_sqr / q.Leq_samples)
            #print(MIC_OFFSET_DB, MIC_REF_DB, Leq_RMS, MIC_REF_AMPL)
        nRF52840_LAeq = MIC_OFFSET_DB + MIC_REF_DB + 20 * math.log(Leq_RMS / MIC_REF_AMPL, 10)
        q.Leq_sum_sqr = 0
        q.Leq_samples = 0

        print("{:.1f} dBA".format(nRF52840_LAeq))

async def mfcc():

#.........mfcc code here.......................
    

async def main():
    laeq_compute = asyncio.create_task(Laeq_computation())
    #mfcc_compute = asyncio.create_task()

    while True:
        await asyncio.sleep_ms(10)
            
    

asyncio.run(main())