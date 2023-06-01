# The MIT License (MIT)
# Copyright (c) 2022 Mike Teachman
# https://opensource.org/licenses/MIT

# Purpose:  Read audio samples from an I2S microphone and write to SD card
#
# - read 32-bit audio samples from I2S hardware, typically an I2S MEMS Microphone
# - convert 32-bit samples to specified bit size and format
# - write samples to a SD card file in WAV format
# - samples will be continuously written to the WAV file
#   for the specified amount of time
#
# uasyncio version

import os
import time
import urandom
import uasyncio as asyncio
from machine import I2S
from machine import Pin
from machine import SDCard

# ======= I2S CONFIGURATION =======

SCK_PIN = 32
WS_PIN = 25
SD_PIN = 33
I2S_ID = 0
BUFFER_LENGTH_IN_BYTES = 40000

# ======= AUDIO CONFIGURATION =======

WAV_FILE = "mic.wav"
RECORD_TIME_IN_SECONDS = 5
WAV_SAMPLE_SIZE_IN_BITS = 16
FORMAT = I2S.MONO
SAMPLE_RATE_IN_HZ = 44100

# ======= AUDIO CONFIGURATION =======

format_to_channels = {I2S.MONO: 1, I2S.STEREO: 2}
NUM_CHANNELS = 1
WAV_SAMPLE_SIZE_IN_BYTES = WAV_SAMPLE_SIZE_IN_BITS // 8
RECORDING_SIZE_IN_BYTES = (RECORD_TIME_IN_SECONDS * SAMPLE_RATE_IN_HZ * WAV_SAMPLE_SIZE_IN_BYTES * NUM_CHANNELS)


def snip_16_mono(samples_in, samples_out):
    num_samples = len(samples_in) // 4
    for i in range(num_samples):
        samples_out[2*i] = samples_in[4*i + 2]
        samples_out[2*i + 1] = samples_in[4*i + 3]        
    return num_samples * 2


def create_wav_header(sampleRate, bitsPerSample, num_channels, num_samples):
    datasize = num_samples * num_channels * bitsPerSample // 8
    o = bytes("RIFF", "ascii")  # (4byte) Marks file as RIFF
    o += (datasize + 36).to_bytes(
        4, "little"
    )  # (4byte) File size in bytes excluding this and RIFF marker
    o += bytes("WAVE", "ascii")  # (4byte) File type
    o += bytes("fmt ", "ascii")  # (4byte) Format Chunk Marker
    o += (16).to_bytes(4, "little")  # (4byte) Length of above format data
    o += (1).to_bytes(2, "little")  # (2byte) Format type (1 - PCM)
    o += (num_channels).to_bytes(2, "little")  # (2byte)
    o += (sampleRate).to_bytes(4, "little")  # (4byte)
    o += (sampleRate * num_channels * bitsPerSample // 8).to_bytes(4, "little")  # (4byte)
    o += (num_channels * bitsPerSample // 8).to_bytes(2, "little")  # (2byte)
    o += (bitsPerSample).to_bytes(2, "little")  # (2byte)
    o += bytes("data", "ascii")  # (4byte) Data Chunk Marker
    o += (datasize).to_bytes(4, "little")  # (4byte) Data size in bytes
    return o


async def record_wav_to_sdcard(audio_in, wav):
    # create header for WAV file and write to SD card
    wav_header = create_wav_header(
        SAMPLE_RATE_IN_HZ,
        WAV_SAMPLE_SIZE_IN_BITS,
        NUM_CHANNELS,
        SAMPLE_RATE_IN_HZ * RECORD_TIME_IN_SECONDS,
    )
    
    num_bytes_written = wav.write(wav_header)
    
    start = time.ticks_us()
    sreader = asyncio.StreamReader(audio_in)
    end = time.ticks_us()
    # allocate sample array
    # memoryview used to reduce heap allocation
    mic_samples = bytearray(10000)
    mic_samples_mv = memoryview(mic_samples)
    #wav_samples = bytearray(5000)
    #wav_samples_mv = memoryview(wav_samples)

    out_samples = bytearray(10000)
    out_samples_mv = memoryview(mic_samples)

    num_sample_bytes_written_to_wav = 0

    # continuously read audio samples from I2S hardware
    # and write them to a WAV file stored on a SD card
    print("Recording size: {} bytes".format(RECORDING_SIZE_IN_BYTES))
    print("==========  START RECORDING ==========")
    
    wavdelay = 0
    while num_sample_bytes_written_to_wav < RECORDING_SIZE_IN_BYTES:
        time_bufferstart = time.ticks_us()
        # read samples from the I2S peripheral
        num_bytes_read_from_mic = await sreader.readinto(mic_samples_mv)
        
        # write samples to WAV file
        if num_bytes_read_from_mic > 0:
            wav_timewrite = time.ticks_us()
            #num_bytes_snipped = snip_16_mono(mic_samples_mv[:num_bytes_read_from_mic], wav_samples_mv)
            #num_bytes_to_write = min(num_bytes_snipped, RECORDING_SIZE_IN_BYTES - num_sample_bytes_written_to_wav)
            num_bytes_to_write = min(num_bytes_read_from_mic, RECORDING_SIZE_IN_BYTES - num_sample_bytes_written_to_wav)
            
            #write wav  
            num_bytes_written = wav.write(mic_samples_mv[:num_bytes_to_write])
            num_sample_bytes_written_to_wav += num_bytes_written
            wav_deduct = time.ticks_diff(time.ticks_us(), wav_timewrite)
            wavdelay += wav_deduct

    print("==========  DONE RECORDING ==========")
    # cleanup
    wav.close()
    audio_in.deinit()
    realend = time.ticks_diff(time.ticks_us(), start);
    print("Block Latency over", RECORD_TIME_IN_SECONDS,  "second:")
    print("Asyncio I2S Data Stream Latency:", time.ticks_diff(end, start)/1000000, "seconds or", time.ticks_diff(end, start), "microseconds")
    #print("Wavdelay", wavdelay/1000000 -5, "seconds")
    print("Asyncio Buffer Write Latency:", realend/1000000 - wavdelay/1000000, "seconds or", realend - wavdelay, "microseconds")
    


async def another_task(name):
    while True:
        await asyncio.sleep(urandom.randrange(2, 5))
        print("{} woke up".format(name))
        time.sleep_ms(10)  # simulates task doing something


async def main(audio_in, wav):
    play = asyncio.create_task(record_wav_to_sdcard(audio_in, wav))
    # keep the event loop active
    while True:
        await asyncio.sleep_ms(10)



audio_in = I2S(
    I2S_ID,
    sck=Pin(SCK_PIN),
    ws=Pin(WS_PIN),
    sd=Pin(SD_PIN),
    mode=I2S.RX,
    bits= 16,
    format=I2S.MONO,
    rate=SAMPLE_RATE_IN_HZ,
    ibuf=BUFFER_LENGTH_IN_BYTES,
    )
    
wav = open("mic.wav", "wb")
asyncio.run(main(audio_in, wav))
wav.close()



audio_in.deinit()
    
#ret = asyncio.new_event_loop()  # Clear retained uasyncio state
