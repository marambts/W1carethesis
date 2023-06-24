import math
import wave
import time
import csv

#start time for block 1
st1 = time.time()

sample_rate = 44100

with wave.open("download.wav") as w:
    print(w.getframerate())
    print(w.getsampwidth())
    print(w.getnchannels())
    print(list(memoryview(w.readframes(100)).cast("h")))

    # Get the audio file parameters
    sample_width = w.getsampwidth()
    num_frames = w.getnframes()

    # Read all frames from the WAV file
    audio_data = w.readframes(num_frames)

audio_data_int = []
sample_rate = 44100

for i in range(0, len(audio_data), sample_width):
    # Convert bytes to integer value
    value = 0
    for j in range(sample_width):
        value |= audio_data[i + j] << (8 * j)

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
        result.append(num / divisor)
    return result


result = max_abs_value(audio_data_int)
audio_data = divide_list(audio_data_int, result)


# Set up the MFCC parameters
duration = len(audio_data) / sample_rate
num_samples = len(audio_data)
num_mfccs = 13
num_filters = 26
filter_bank = []
for i in range(num_filters):
    filter_bank.append([])

#end time for block 1
et1 = time.time()

#start time for block 2
st2 = time.time()

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

#end time for block 2
et2 = time.time()

#get the start time for block 3
st3 = time.time()

# Compute the MFCCs
mfccs = []

num_chunks = num_samples // num_samples
for chunk_idx in range(num_chunks):
    # Extract a chunk of audio data
    start_idx = chunk_idx * 512
    end_idx = min((chunk_idx + 1) * 512, num_samples)
    audio_chunk = audio_data[start_idx:end_idx]

    # Compute the power spectrum
    power_spectrum = [0] * len(audio_chunk)
    for i in range(len(audio_chunk)):
        power_spectrum[i] = abs(audio_chunk[i]) ** 2

    #end time for block 3
    et3 = time.time()

    #start time for block 4
    st4 = time.time()

    # Apply the filter bank
    filter_bank_energies = [0] * num_filters
    for i in range(num_filters):
        filter_energy = 0
        for j in range(len(filter_bank[i])):
            if j < len(power_spectrum):
                filter_energy += filter_bank[i][j] * power_spectrum[j]
        filter_bank_energies[i] = math.log(filter_energy + 1e-6)

    #end time for block 4
    et4 = time.time()

    #start time for block 5
    st5 = time.time()

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

#end time for block 5
et5 = time.time()

print("MFCCs mean:", mfccs_mean)

# get the execution time
elapsed_time1 = et1 - st1
print('Execution time (framing and windowing):', elapsed_time1, 'seconds')

# get the execution time
elapsed_time2 = et2 - st2
print('Execution time (windowing and fft):', elapsed_time2, 'seconds')

# get the execution time
elapsed_time3 = et3 - st3
print('Execution time (mel-filter bank):', elapsed_time3, 'seconds')

# get the execution time
elapsed_time4 = et4 - st4
print('Execution time (DCT):', elapsed_time4, 'seconds')

# get the execution time
elapsed_time5 = et5 - st5
print('Execution time (cepstral coefficient):', elapsed_time5, 'seconds')

#sum
time = elapsed_time5 + elapsed_time4 + elapsed_time3 + elapsed_time2 + elapsed_time1
print('Execution time(sum) :', time, 'seconds')

# overall execution time
elapsed_time = et5 - st1
print('Execution time:', elapsed_time, 'seconds')

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