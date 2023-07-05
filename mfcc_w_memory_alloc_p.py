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
        #self.Leq_dB = 0

q = sum_queue_t()

#............Sampling Initialization..............
SAMPLE_RATE = 44100 #Hz
SAMPLE_BITS = 16 #BITS
SAMPLES_SHORT = SAMPLE_RATE/8 #~125ms                                                     
SAMPLES_LEQ = (SAMPLE_RATE*LEQ_PERIOD)                                                    
                                                      
#................I2S pin mapping..................
sck_pin = 32   # Serial clock output
ws_pin = 25    # Word clock output
sd_pin = 33   # Serial data output
I2S_ID = 0                                                   

#.................audio configuration...................
BUFFER_LENGTH_IN_BYTES = 8192
SAMPLE_SIZE_IN_BITS = 16
FORMAT = I2S.MONO
SAMPLE_RATE_IN_HZ = 44100
sample_width = 2
audio_data_int = []
sample_rate = 44100


#..............main code here..........................

#initialize buffer size
mic_samples = bytearray(int(SAMPLES_SHORT))
mic_samples_mv = memoryview(mic_samples)                                              
ESP32_LAeq = 0

def i2s_callback_rx(arg):
    global mic_samples_mv
    
    #buffer_array = [int(i) for i in mic_samples_mv]
    q.sum_sqr_weighted = [int(i) for i in mic_samples_mv]
    
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

for i in range(0, len(mic_samples_mv), sample_width):
    # Convert bytes to integer value
    value = 0
    for j in range(sample_width):
        value |= mic_samples_mv[i + j] << (8 * j)

    # Handle negative values
    if value >= (1 << (8 * sample_width - 1)):
        value -= 1 << (8 * sample_width)

    audio_data_int.append(value)

def max_abs_value(lst):
    max_abs = None
    for num in lst:
        abs_val = abs(num)
        if max_abs is None or abs_val > max_abs:
            max_abs = abs_val
    return max_abs

def divide_list(lst, divisor):
    result = []
    for num in lst:
        result.append(num / 1)
    return result


result = max_abs_value(audio_data_int)
audio_data = divide_list(audio_data_int, result)

# Set up the MFCC parameters
duration = len(mic_samples_mv) / sample_rate
num_samples = len(mic_samples_mv)
num_mfccs = 13
num_filters = 26
filter_bank = []
for i in range(num_filters):
    filter_bank.append([])

# Compute the filter bank
for i in range(num_filters):
    for j in range(sample_rate // 2):
        freq = j / sample_rate
        if freq >= (i * 1000 / 700) and freq <= ((i + 2) * 1000 / 700):
            filter_bank[i].append((freq - i * 1000 / 700) / (1000 / 700))
        elif freq >= ((i + 1) * 1000 / 700) and freq <= ((i + 3) * 1000 / 700):
            filter_bank[i].append(((i + 3) * 1000 / 700 - freq) / (1000 / 700))
        else:
            filter_bank[i].append(0)

# Compute the MFCCs
mfccs = []

num_chunks = num_samples // num_samples
for chunk_idx in range(num_chunks):
    # Extract a chunk of audio data
    start_idx = chunk_idx * 512
    end_idx = min((chunk_idx + 1) * 512, num_samples)
    audio_chunk = mic_samples_mv[start_idx:end_idx]

    # Compute the power spectrum
    power_spectrum = [0] * len(audio_chunk)
    for i in range(len(audio_chunk)):
        power_spectrum[i] = abs(audio_chunk[i]) ** 2

    # Apply the filter bank
    filter_bank_energies = [0] * num_filters
    for i in range(num_filters):
        filter_energy = 0
        for j in range(len(filter_bank[i])):
            if j < len(power_spectrum):
                filter_energy += filter_bank[i][j] * power_spectrum[j]
        filter_bank_energies[i] = math.log(filter_energy + 1e-6)

    # Compute the MFCCs
    mfccs_chunk = [0] * num_mfccs
    for i in range(num_mfccs):
        mfcc_val = 0
        for j in range(num_filters):
            mfcc_val += filter_bank_energies[j] * math.cos(math.pi * i / num_filters * (j + 0.5))
        mfccs_chunk[i] = mfcc_val
    mfccs.append(mfccs_chunk)

# Print the MFCCs and their mean
for i in range(len(mfccs)):
    print("MFCCs for chunk", i, ":", mfccs[i])

    for y in range(len(mfccs[i])):
        t = mfccs[i][y]
    print(type(t))

mfccs_mean = [0] * num_mfccs
for i in range(num_mfccs):
    mfccs_mean[i] = sum([mfccs[j][i] for j in range(len(mfccs))]) / len(mfccs)

print("MFCCs mean:", mfccs_mean)

def save_mfccs_to_csv(mfccs, filename):
    with open(filename, "w", newline="") as csvfile:
        writer = csv.writer(csvfile, delimiter=",")
        for chunk_mfccs in mfccs:
            writer.writerow(chunk_mfccs)

if __name__ == "__main__":
    mfccs = []
    for chunk_idx in range(num_chunks):
        chunk_mfccs = []
        for i in range(num_mfccs):
            chunk_mfccs.append(mfccs_chunk[i])
        mfccs.append(chunk_mfccs)

    save_mfccs_to_csv(mfccs, "mfccs.csv")

#librosa.feature.inverse.mfcc_to_audio(mfccs, *, num_mfccs=13, dct_type=2, norm='ortho', ref=1.0, lifter=0, **kwargs)
