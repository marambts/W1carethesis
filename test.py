import machine
from machine import I2S
from machine import Pin
import uasyncio as asyncio
gc.enable()
gc.collect()
 
BUFFER_LENGTH_IN_BYTES = 40000
WAV_SAMPLE_SIZE_IN_BITS = 16
FORMAT = I2S.MONO
SAMPLE_RATE_IN_HZ = 16000
 
sck_pin = 32   # Serial clock output
ws_pin = 25    # Word clock output
sd_pin = 33    # Serial data output
I2S_ID = 0 #where used?

audio_in = I2S(
        I2S_ID,
        sck=Pin(sck_pin),
        ws=Pin(ws_pin),
        sd=Pin(sd_pin),
        mode=I2S.RX,
        bits=WAV_SAMPLE_SIZE_IN_BITS,
        format=FORMAT,
        rate=SAMPLE_RATE_IN_HZ,
        ibuf=BUFFER_LENGTH_IN_BYTES,
    )


# Buffer to store the audio data
buf_size = 1024  # Adjust the buffer size as per your requirements
audio_buffer = bytearray(buf_size)
audio_buffer_mv = memoryview(audio_buffer)

# Coroutine function to continuously read audio data
async def read_audio_data(audio_in):
    gcstart = gc.mem_free()
    while True:
        # Read audio data into the buffer
        
        sreader = asyncio.StreamReader(audio_in)
        #num_read = await sreader.readinto(audio_buffer)

        # Process the audio data as per your requirement
        # Here, we simply print the raw data as an example
        print(sreader)
        print("Bytes of RAM heap used:", gcstart-gc.mem_free())
        

async def main(audio_in):
    i2s_stream = asyncio.create_task(read_audio_data(audio_in))
    while True:
        await asyncio.sleep_ms(10)
        
asyncio.run(main(audio_in))