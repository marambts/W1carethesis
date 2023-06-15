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

#Configuration
LEQ_PERIOD = 1

#values from microphone datasheet
MIC_OFFSET_DB = 3.0103 #for short_spl_db
MIC_SENSITIVITY = -26 #where used?
MIC_REF_DB = 94 #for short_spl_db
MIC_OVERLOAD_DB = 120.0 #dB - Acoustic overload point
MIC_NOISE_DB = -87 # dB - Noise floor
MIC_BITS = 24 #mic_ref_ampl

#def MIC_CONVERT(s): 
    #return s >> (SAMPLE_BITS - MIC_BITS) #this is --> define MIC_CONVERT(s) (s >> (SAMPLE_BITS - MIC_BITS))
    #used when converting the int mic values to floats but is already removed in the reader task

#Calculate reference amplitude value at compile time
#no concept of consterpx or pow function w double precision like in C++
#consterpx does the process in compiler time instead of runtime, saving time and storage
MIC_REF_AMPL = math.pow(10, (MIC_SENSITIVITY)/20) * ((1<<(MIC_BITS-1)-1)) #for short_spl_db                                                                                                                                                                                                                            
       

#necessity of this class is based on how filters will be done
class sum_queue_t: 
    def __init__(self):
        self.buffer = 0.0
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
n = 690 #number of samples needed for 1 sec LAeq evaluation: 5512, 5512/8 = 689

#buffer for sampling
buffer = bytearray(n) #what is the appropriate size?
#calculated samples
buffer_mv = memoryview(buffer) # provides a way to access the
                #underlying data of an object supporting the buffer protocol without creating a new copy of the data                                               
                #memoryview allows you to work directly with the lower level languages, no need to get everything everytime, saves time drastically

#where filtered data will be stored for LAeq computation
laeq_array = []

#audio configuration
BUFFER_LENGTH_IN_BYTES = 40000
SAMPLE_SIZE_IN_BITS = 16
FORMAT = I2S.MONO
SAMPLE_RATE_IN_HZ = 16000

# I2S Microphone sampling setup
async def mic_i2s_sampling():
    
    #uasyncio I2S config
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
    
    #streamed audio is read and put in buffer
    num_read = await sreader.readinto(buffer_mv)
    #print(buffer_mv)

#Inputs raw audio samples for filtering and outputs filtered data
async def audio_filter():
    global q
    global laeq_array
    q.clear_filters()
    
    await mic_i2s_sampling()
    
    #this is the input for the filters
    #we convert the stream object to int
    buffer_array = [int(i) for i in buffer_mv]
    #print(buffer_array)
    
   
    #code for filters
    
    q.sum_sqr_SPL.extend(sum_buffer)
    q.sum_sqr_weighted.extend(sum_buffer)
    
    #i assume here that the outputs of the filtered data are put in an array
    laeq_array.extend('IIR filter ouput variable')
    #print(laeq_array)


async def clear_data():
    global buffer
    global buffer_mv
    
    #temp functions
    #set to 0 so it can load up again

    n_clear = 0
    buffer = bytearray(n_clear)
    buffer_mv = memoryview(buffer)
    gc.collect()

#
#Setup and main loop
#

async def laeq_computations():
    
    # If needed, now you can actually lower the CPU frequency,
    # i.e. if you want to (slightly) reduce ESP32 power consumption
    machine.freq(80000000) # It should run as low as 80MHz
    uart = UART(0, 115200)
    #device-to-device communication, mic to esp32                                               
    asyncio.sleep_ms(1000) # Safety
    
    rms_array = []
    Leq_samples = []
    Leq_sum_sqr = []
    Leq_dB = []
    
    #each iteration samples raw audio data, gets filtered data, puts in an array then clears data for the next iteration
    #this is not queueing but rather alternative for the 8 blocks
    iterations = 8 #125ms * 8 = 1s
    for i in range(iterations): #for loop buffers
        if i == 1:
            await audio_filter()
            Leq_sum_sqr.extend(q.sum_sqr_weighted)
            #i think there is smth wrong here mathematically
            Leq_samples += [Leq_sum_sqr[i] + SAMPLES_SHORT[i] for i in range(len(Leq_samples))]
            clear_data()
        else:
            await audio_filter()
            Leq_sum_sqr = [Leq_sum_sqr[i] + q.sum_sqr_weighted[i] for i in range(len(Leq_sum_sqr))]
            #i think there is smth wrong here mathematically
            Leq_samples += [Leq_sum_sqr[i] + SAMPLES_SHORT[i] for i in range(len(Leq_samples))]
            rms_array.extend(q.sum_sqr_SPL)
            clear_data()
            
            
    #before it enters the while statement, all filtered data should have been added and stored in Leq_sum_sqr and Leq_samples

    while True: #while loop buffers
        #since q.sum_sqr_SPL is expected to input an array, short_RMS and short_SPL_dB outputs an array as well
        short_RMS = [math.sqrt(rms_array[i] / SAMPLES_SHORT) for i in range(len(rms_array))]
        short_SPL_dB = []
        #for value in short_RMS:
            #spl_db = MIC_OFFSET_DB + MIC_REF_DB + (20 * math.log10(value/MIC_REF_AMPL))
            #spl_db = MIC_OFFSET_DB + MIC_REF_DB + 20 * math.log10(value / MIC_REF_AMPL)
            #short_SPL_dB.append(spl_db)
        #short_SPL_dB = [(MIC_OFFSET_DB + MIC_REF_DB +(20* math.log10(value/MIC_REF_AMPL))) for value in short_RMS]
        for value in short_RMS:
            if value > 0:
                spl_db = MIC_OFFSET_DB + MIC_REF_DB + 20 * math.log10(value / MIC_REF_AMPL)
            else:
                spl_db = float('-inf')  # or any other appropriate value
                short_SPL_dB.append(spl_db)   

        # In case of acoustic overload or below noise floor measurement, report infinity Leq value
        #This still assumes that short_SPL_dB returns an array of values
        if any(value >MIC_OVERLOAD_DB for value in short_SPL_dB):
            Leq_sum_sqr = float('inf')
        elif any(math.isnan(value) or (value < MIC_NOISE_DB) for value in short_SPL_dB):
        #elif any(math.isnan(short_SPL_dB) or (short_SPL_dB < MIC_NOISE_DB) for value in short_SPL_dB):
            Leq_sum_sqr = float('-inf')
                
        # Accumulate Leq sum
        

        # When we gather enough samples, calculate new Leq value
        for i in range(len(Leq_samples)):
            if Leq_samples[i] >= (SAMPLE_RATE*LEQ_PERIOD):
                Leq_RMS = math.sqrt(Leq_sum_sqr[i]/Leq_samples[i])
                Leq_dB = MIC_OFFSET_DB + MIC_REF_DB + (20 * math.log10(Leq_RMS/MIC_REF_AMPL))
                print("{:.1f} dBA".format(Leq_dB))
            else:
                print('Error in LAeq Reading...')
                
        rms_array = []
        Leq_samples = []
        Leq_sum_sqr = []
        Leq_dB = []
        
            
async def main():
    i2s_stream = asyncio.create_task(laeq_computations())
    
    while True:
        await asyncio.sleep_ms(10)
        
asyncio.run(main())       



