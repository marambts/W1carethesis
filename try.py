import math
import wave
import numpy as np
import time


def read_wave_file(filename):
    with wave.open(filename) as w:
        print(w.getframerate())
        print(w.getsampwidth())
        print(w.getnchannels())

        num_frames = w.getnframes()
        return w.readframes(num_frames)

def convert_bytes_to_array(audio_data):
    return np.frombuffer(audio_data, dtype=np.int16)

def normalize(audio_data):
    return audio_data / max(abs(audio_data))

def compute_filter_bank(sample_rate, num_filters):
    filter_bank = []
    for i in range(num_filters):
        filter_bank.append([])

    for i in range(num_filters):
        for j in range(sample_rate // 2):
            freq = j / sample_rate
            if freq >= (i * 1000 / 700) and freq <= ((i + 2) * 1000 / 700):
                filter_bank[i].append((freq - i * 1000 / 700) / (1000 / 700))
            elif freq >= ((i + 1) * 1000 / 700) and freq <= ((i + 3) * 1000 / 700):
                filter_bank[i].append(((i + 3) * 1000 / 700 - freq) / (1000 / 700))
            else:
                filter_bank[i].append(0)

    return filter_bank


def compute_mfccs(audio_data, sample_rate, num_samples, num_mfccs, num_filters, filter_bank):
    mfccs = []
    num_chunks = num_samples // num_samples
    for chunk_idx in range(num_chunks):
        start_idx = chunk_idx * 512
        end_idx = min((chunk_idx + 1) * 512, num_samples)
        audio_chunk = audio_data[start_idx:end_idx]
        power_spectrum = [0] * len(audio_chunk)
        for i in range(len(audio_chunk)):
            power_spectrum[i] = abs(audio_chunk[i]) ** 2

        filter_bank_energies = [0] * num_filters
        for i in range(num_filters):
            filter_energy = 0
            for j in range(len(filter_bank[i])):
                if j < len(power_spectrum):
                    filter_energy += filter_bank[i][j] * power_spectrum[j]
            filter_bank_energies[i] = math.log(filter_energy + 1e-6)

        mfccs_chunk = [0] * num_mfccs
        for i in range(num_mfccs):
            mfcc_val = 0
            for j in range(num_filters):
                mfcc_val += filter_bank_energies[j] * math.cos(math.pi * i / num_filters * (j + 0.5))
            mfccs_chunk[i] = mfcc_val
        mfccs.append(mfccs_chunk)

    return mfccs


def compute_mfccs_mean(mfccs):
    num_mfccs = len(mfccs[0])
    mfccs_mean = [0] * num_mfccs
    for i in range(num_mfccs):
        mfccs_mean[i] = sum([mfccs[j][i] for j in range(len(mfccs))]) / len(mfccs)
    return mfccs_mean


# Start time for block 1
st1 = time.time()

audio_data = read_wave_file("recording_1s.wav")
sample_width = 2
audio_data_int = convert_bytes_to_array(audio_data)
#audio_data = normalize(audio_data_int)

# Set up the MFCC parameters
sample_rate = 44100
num_samples = len(audio_data)
num_mfccs = 13
num_filters = 26

# End time for block 1
et1 = time.time()

# Start time for block 2
st2 = time.time()

filter_bank = compute_filter_bank(sample_rate, num_filters)

# End time for block 2
et2 = time.time()

# Start time for block 3
st3 = time.time()

mfccs = compute_mfccs(audio_data, sample_rate, num_samples, num_mfccs, num_filters, filter_bank)

# End time for block 3
et3 = time.time()

# Start time for block 4
st4 = time.time()

mfccs_mean = compute_mfccs_mean(mfccs)

# End time for block 4
et4 = time.time()

st5 = time.time()
# Print the MFCCs and their mean
for i in range(len(mfccs)):
    print("MFCCs for chunk", i, ":", mfccs[i])

    for y in range(len(mfccs[i])):
        t = mfccs[i][y]
    print(type(t))

# End time for block 5
et5 = time.time()

# Get the execution times
elapsed_time1 = et1 - st1
elapsed_time2 = et2 - st2
elapsed_time3 = et3 - st3
elapsed_time4 = et4 - st4
elapsed_time5 = et5 - st5

# Compute the sum of execution times
time = elapsed_time5 + elapsed_time4 + elapsed_time3 + elapsed_time2 + elapsed_time1

# Overall execution time
elapsed_time = et5 - st1

print("MFCCs mean:", mfccs_mean)
print("Execution time (framing and windowing):", elapsed_time1, "seconds")
print("Execution time (windowing and fft):", elapsed_time2, "seconds")
print("Execution time (mel-filter bank):", elapsed_time3, "seconds")
print("Execution time (DCT):", elapsed_time4, "seconds")
print("Execution time (cepstral coefficient):", elapsed_time5, "seconds")
print("Execution time (sum):", time, "seconds")
print("Overall execution time:", elapsed_time, "seconds")

