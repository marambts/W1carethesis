# ************************
import machine
import math
import utime as time
import array

# I2S sensor initializations
import os
import uasyncio as asyncio
from machine import I2S
from machine import Pin
from machine import UART

gc.enable()
gc.collect()

#Configuration
LEQ_PERIOD = 1 #where used?
USE_DISPLAY = 1 #where used?

#values from microphone datasheet
MIC_OFFSET_DB = 3.0103 #for short_spl_db
MIC_SENSITIVITY = -26 #where used?
MIC_REF_DB = 94 #for short_spl_db
MIC_OVERLOAD_DB = 120.0 #dB - Acoustic overload point
MIC_BITS = 24 #mic_ref_ampl
MIC_NOISE_DB = -87 # dB - Noise floor
MIC_TIMING_SHIFT = 0   #where used?

MIC_REF_AMPL = math.pow(10, (MIC_SENSITIVITY)/20) * ((1<<(MIC_BITS-1)-1)) #for short_spl_db                                                                                                                                                                                                                            
       

# Necessity of this class is based on how filters will be done
class sum_queue_t:
    def __init__(self):
        # Sum of squares of mic samples, after Equalizer filter
        self.sum_sqr_SPL = []
        # Sum of squares of weighted mic samples
        self.sum_sqr_weighted = []
        self.Leq_sum_sqr = 0
        self.Leq_samples = 0

q = sum_queue_t()

# Sampling
#Sampling
SAMPLE_RATE = 44100 #Hz, fixed to design of IIR filters, formerly 48kHz
SAMPLE_BITS = 32 #BITS
SAMPLE_T = 0 #int32_t
SAMPLES_SHORT = SAMPLE_RATE/8 #~125ms                                                     
SAMPLES_LEQ = (SAMPLE_RATE*LEQ_PERIOD)
DMA_BANK_SIZE = (SAMPLES_SHORT/16)
DMA_BANKS = 32                                                      
                                                      
# I2S pin mapping
# ESP32
sck_pin = 32   # Serial clock output
ws_pin = 25    # Word clock output
sd_pin = 33   # Serial data output
I2S_ID = 0 #where used?                                                    

#audio configuration
BUFFER_LENGTH_IN_BYTES = 40000
SAMPLE_SIZE_IN_BITS = 16
FORMAT = I2S.MONO
SAMPLE_RATE_IN_HZ = 44100
mic_samples = bytearray(int(SAMPLES_SHORT))
#mic_samples = bytearray(1000)
mic_samples_mv = memoryview(mic_samples)
#machine.freq(80000000) # It should run as low as 80MHz
#uart = UART(0, 115200)                                               

gc_start = gc.mem_free()

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
    machine.freq(80000000) # It should run as low as 80MHz
    uart = UART(0, 115200)
    

    iterations = 8 #number of iterations to reach 44.1k samples
    for i in range(iterations):
        sampling()
        
        short_SPL_dB = 0
        short_RMS = math.sqrt(sum(q.sum_sqr_SPL) / SAMPLES_SHORT)
                
        if short_RMS < 8.797: #this is based on raw samples, might change for filters
            pass
        else:
            short_SPL_dB = MIC_OFFSET_DB + MIC_REF_DB + (20 * math.log10(short_RMS / MIC_REF_AMPL))
                
                
        if short_SPL_dB > MIC_OVERLOAD_DB:
            q.Leq_sum_sqr = float('inf')
        elif math.isnan(short_SPL_dB) or (short_SPL_dB < MIC_NOISE_DB):
            q.Leq_sum_sqr = float('-inf')

        q.Leq_sum_sqr += sum(q.sum_sqr_weighted)
        q.Leq_samples += SAMPLES_SHORT
        #print(sum(q.sum_sqr_SPL), short_RMS, q.Leq_samples)
        
    if q.Leq_samples >= SAMPLE_RATE * LEQ_PERIOD:
        #print(q.Leq_sum_sqr)
        Leq_RMS = math.sqrt(q.Leq_sum_sqr / q.Leq_samples)
        #print(MIC_OFFSET_DB, MIC_REF_DB, Leq_RMS, MIC_REF_AMPL)
        Leq_dB = MIC_OFFSET_DB + MIC_REF_DB + 20 * math.log10(Leq_RMS / MIC_REF_AMPL)
        q.Leq_sum_sqr = 0
        q.Leq_samples = 0

        print("{:.1f} dBA".format(Leq_dB))
        #break #remove if you want it to continuously run
            
    if len(q.sum_sqr_SPL) > SAMPLES_SHORT:
        q.sum_sqr_SPL.pop(0)
    if len(q.sum_sqr_weighted) > SAMPLES_SHORT:
        q.sum_sqr_weighted.pop(0)
    
    end = time.ticks_us()
    print("LAeq Reading Latency:", time.ticks_diff(end, start)/1000000, "seconds or", time.ticks_diff(end, start), "microseconds")

        
while True:
    gc_start = gc.mem_free()
    laeq_computation()
    gc.mem_free()
    print("Memory Allocation:", gc_start, "bytes of heap RAM are allocated")
    print("Free Memory Left:", gc.mem_free(), "bytes of available heap RAM")
    print("Memory Used:", gc_start - gc.mem_free(), "bytes of heap RAM used")
    time.sleep_ms(100)


       