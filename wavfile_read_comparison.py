import wave
from scipy.io import wavfile
import numpy as np

def read_wave_file(filename):
    with wave.open(filename) as w:
        print(w.getframerate())
        print(w.getsampwidth())
        print(w.getnchannels())

        num_frames = w.getnframes()
        return w.readframes(num_frames)


def convert_bytes_to_int(audio_data, sample_width):
    audio_data_int = []
    value = 0
    for i in range(len(audio_data)):
        byte = audio_data[i]
        value |= byte << (8 * (i % sample_width))

        if i % sample_width == sample_width - 1:
            if value >= (1 << (8 * sample_width - 1)):
                value -= 1 << (8 * sample_width)
            audio_data_int.append(value)
            value = 0

    #print(audio_data_int)
    return audio_data_int

audio_data = read_wave_file("recording_1s.wav")
sample_width = 2
audio_data_int = convert_bytes_to_int(audio_data, sample_width)
audio_data_int_np = np.frombuffer(audio_data, dtype=np.int16)
print(type(audio_data_int))
print(type(audio_data_int_np))

samplerate, data = wavfile.read("recording_1s.wav")
print(data)
print(type(data))
print(audio_data_int_np == data)