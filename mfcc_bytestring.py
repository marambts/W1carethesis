import adafruit_wave
import time

with adafruit_wave.open("recording_1s.wav") as w:
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

# Example usage
result = max_abs_value(audio_data_int)
audio_data = divide_list(audio_data_int, result)

print(filter_bank)

print(result)
print(audio_data)
