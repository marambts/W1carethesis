import math
import wave
import time
import csv


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


def compute_mfccs(audio_data):
    # Set up the MFCC parameters
    sample_rate = 44100
    num_samples = len(audio_data)
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
        audio_chunk = audio_data[start_idx:end_idx]

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

    return mfccs


# Read the audio file
with wave.open("download.wav") as w:
    sample_rate = w.getframerate()
    sample_width = w.getsampwidth()
    num_frames = w.getnframes()

    # Prepare the buffer for reading audio data
    buffer_size = 512
    buffer = bytearray(buffer_size * sample_width)

    # Initialize the MFCCs list
    mfccs = []

    # Read and process audio data in chunks
    while True:
        # Read a chunk of audio data into the buffer
        buffer_data = w.readframes(buffer_size)

        # If there's no more data in the buffer, break the loop
        if not buffer_data:
            break

        # Convert the buffer data to a list of integers
        audio_data = []
        for i in range(0, len(buffer_data), sample_width):
            value = 0
            for j in range(sample_width):
                value |= buffer_data[i + j] << (8 * j)
            if value >= (1 << (8 * sample_width - 1)):
                value -= 1 << (8 * sample_width)
            audio_data.append(value)

        # Compute the MFCCs for the chunk
        mfccs_chunk = compute_mfccs(audio_data)

        # Add the computed MFCCs to the list
        mfccs.extend(mfccs_chunk)

# Print the MFCCs and their mean
for i in range(len(mfccs)):
    print("MFCCs for chunk", i, ":", mfccs[i])

mfccs_mean = [sum(col) / len(mfccs) for col in zip(*mfccs)]
print("MFCCs mean:", mfccs_mean)


