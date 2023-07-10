import machine
import math
import struct
import array
from machine import I2S, Pin

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
    mfcc = [0] * NUM_CEPSTRUM

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

    # Compute Discrete Cosine Transform (DCT) of log Mel spectrum
    for i in range(NUM_CEPSTRUM):
        for j in range(NUM_FILTERS):
            mfcc[i] += log_mel_spectrum[j] * math.cos(math.pi * i / NUM_FILTERS * (j + 0.5))
    
    print("MFCC Coeff: ", mfcc)

# Create an ADC object

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
        time.sleep_ms(1)
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
    mfcc = compute_mfcc(audio_data, SAMPLE_RATE)

        # Print MFCC coefficients
    #print(mfcc)
# Run the main function
main()
