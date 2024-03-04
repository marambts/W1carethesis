import math
import array
import time
import micropython
from machine import I2S, Pin

# Set up the MFCC parameters
num_mfccs = 10
num_filters = 13
filter_bank = [[] for _ in range(num_filters)]

def compute_filter_bank(sample_rate):
    for i in range(num_filters):
        filter_bank[i].clear()
        for j in range(sample_rate // 2):
            freq = j / sample_rate
            if freq >= (i * 1000 / 700) and freq <= ((i + 2) * 1000 / 700):
                filter_bank[i].append((freq - i * 1000 / 700) / (1000 / 700))
                filter_bank[i].pop()
            elif freq >= ((i + 1) * 1000 / 700) and freq <= ((i + 3) * 1000 / 700):
                filter_bank[i].append(((i + 3) * 1000 / 700 - freq) / (1000 / 700))
                filter_bank[i].pop()
            else:
                filter_bank[i].append(0)
                filter_bank[i].pop()

def compute_mfccs(mic_samples, sample_rate):
    num_samples = len(mic_samples)
    num_chunks = num_samples // 512
    mfccs = []

    for chunk_idx in range(num_chunks):
        start_idx = chunk_idx * 512
        end_idx = min((chunk_idx + 1) * 512, num_samples)
        audio_chunk = mic_samples[start_idx:end_idx]

        power_spectrum = [abs(sample) ** 2 for sample in audio_chunk]

        filter_bank_energies = [0] * num_filters
        for i in range(num_filters):
            filter_energy = sum(filter_bank[i][j] * power_spectrum[j] for j in range(len(filter_bank[i])) if j < len(power_spectrum))
            filter_bank_energies[i] = math.log(filter_energy + 1e-6)

        mfccs_chunk = [sum(filter_bank_energies[j] * math.cos(math.pi * i / num_filters * (j + 0.5)) for j in range(num_filters)) for i in range(num_mfccs)]
        mfccs.append(mfccs_chunk)

    return mfccs

# I2S pin mapping
sck_pin = 32  # Serial clock output
ws_pin = 25  # Word clock output
sd_pin = 33  # Serial data output
I2S_ID = 0

# Audio configuration
BUFFER_LENGTH_IN_BYTES = 8192
FORMAT = I2S.MONO
sample_rate_IN_HZ = 44100
sample_width = 2
audio_data_int = []

# Initialize buffer size
mic_samples = bytearray(int(sample_rate_IN_HZ / 8))

# I2S callback for receiving audio samples
def i2s_callback_rx(arg):
    global mic_samples_mv
    q.sum_sqr_weighted = array.array("i", mic_samples_mv)

# Sampling Initialization
audio_in = I2S(
    I2S_ID,
    sck=Pin(sck_pin),
    ws=Pin(ws_pin),
    sd=Pin(sd_pin),
    mode=I2S.RX,
    bits=16,
    format=FORMAT,
    rate=sample_rate_IN_HZ,
    ibuf=BUFFER_LENGTH_IN_BYTES,
)
time.sleep_ms(100)
audio_in.irq(i2s_callback_rx)
num_read = audio_in.readinto(mic_samples)
time.sleep_ms(100)

# Example usage
compute_filter_bank(sample_rate_IN_HZ)
mfccs = compute_mfccs(mic_samples, sample_rate_IN_HZ)

# Print the MFCCs and their mean
for i, mfccs_chunk in enumerate(mfccs):
    print("MFCCs for chunk", i, ":", mfccs_chunk)

mfccs_mean = [sum(mfccs[j][i] for j in range(len(mfccs))) / len(mfccs) for i in range(num_mfccs)]
print("MFCCs mean:", mfccs_mean)

def save_mfccs_to_csv(mfccs, filename):
    with open(filename, "w", newline="") as csvfile:
        writer = csv.writer(csvfile, delimiter=",")
        for chunk_mfccs in mfccs:
            writer.writerow(chunk_mfccs)

if __name__ == "__main__":
    save_mfccs_to_csv(mfccs, "mfccs.csv")
