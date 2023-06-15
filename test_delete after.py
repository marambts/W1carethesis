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


#Memory Manipulation
gc.enable()
gc.collect()

#Configuration
LEQ_PERIOD = 1

#values from microphone datasheet
MIC_OFFSET_DB = 3.0103 #for short_spl_db
MIC_SENSITIVITY = -26 
MIC_REF_DB = 94 #for short_spl_db
MIC_OVERLOAD_DB = 120.0 #dB - Acoustic overload point
MIC_NOISE_DB = -87 # dB - Noise floor
MIC_BITS = 24 #mic_ref_ampl

MIC_REF_AMPL = math.pow(10, (MIC_SENSITIVITY)/20) * ((1<<(MIC_BITS-1)-1)) #for short_spl_db                                                                                                                                                                                                                            
       
class sum_queue_t: 
    def __init__(self):
        # Sum of squares of mic samples, after Equalizer filter
        self.sum_sqr_SPL = []
        # Sum of squares of weighted mic samples
        self.sum_sqr_weighted = []
    def clear_filters(self):
        self.sum_sqr_SPL = []
        self.sum_sqr_weighted = []

q = sum_queue_t()

#Sampling
SAMPLE_RATE = 441000 #Hz, fixed to design of IIR filters, formerly 48kHz
SAMPLE_BITS = 32 #BITS
SAMPLE_T = 0 #int32_t
SAMPLES_SHORT = (SAMPLE_RATE/8) #~125ms                                                     
SAMPLES_LEQ = (SAMPLE_RATE*LEQ_PERIOD)
DMA_BANK_SIZE = (SAMPLES_SHORT/16)
DMA_BANKS = 32                                                      
                                                      
# I2S pin mapping
# ESP32
sck_pin = 32   # Serial clock output
ws_pin = 25    # Word clock output
sd_pin = 33   # Serial data output
I2S_ID = 0 #where used?                                                    
laeq_array = []

#audio configuration
BUFFER_LENGTH_IN_BYTES = 40000
SAMPLE_SIZE_IN_BITS = 16
FORMAT = I2S.MONO
SAMPLE_RATE_IN_HZ = 16000


n = 1000 
#buffer for sampling
buffer = bytearray(n) #what is the appropriate size?
#calculated samples
buffer_mv = memoryview(buffer) 
#where filtered data will be stored for LAeq computation

# I2S Microphone sampling setup
async def mic_i2s_sampling():
    gc_start = gc.mem_free()
    #uasyncio I2S config
    start = time.ticks_us()
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
    
    #for inmp441 start up time ~83ms
    await asyncio.sleep_ms(100)
    
    #samples and streams the audio data
    sreader = asyncio.StreamReader(audio_in)
    
    while True:
        #streamed audio is read and put in buffer
        num_read = await sreader.readinto(buffer_mv)
        # Process the audio samples or perform any necessary operations
        buffer_array = [int(i) for i in buffer_mv]
        print(buffer_array)

asyncio.run(mic_i2s_sampling())       