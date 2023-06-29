import adafruit_wave as wave
import time
import ulab
from ulab import numpy as np
from ulab import scipy


# Hamming window function
def hamming_window(length):
    return 0.54 - 0.46 * np.cos(2 * np.pi * np.arange(length) / (length - 1))


# Mel Filterbank computation (note that this is fixed for num_filters = 26, fft_size =512, sample_rate = 44100)
def mel_filterbank():
    mel_filterbank = [0, 1, 2, 3, 5, 7, 9, 11, 14, 17, 21, 25, 30,
                      35, 41, 48, 55, 64, 74, 86, 99, 113, 130, 149, 171, 196,
                      224, 256]
    return np.array(mel_filterbank)


# DCT (Discrete Cosine Transform) computation
def dct(signal):
    N = len(signal)
    n = np.arange(N)
    k = n.reshape((N, 1))
    cos_term = np.cos(np.pi * k * (2 * n + 1) / (2 * N))
    dct_result = np.dot(signal, cos_term)
    yield dct_result


# MFCC (Mel Frequency Cepstral Coefficients) computation
def mfcc(signal, sample_rate):
    # Apply Mel filterbank
    mel_filterbank_arr = mel_filterbank()
    num_filters = len(mel_filterbank_arr)
    fft_size = len(signal)
    mel_energies = np.dot(signal ** 2, mel_filterbank_arr.T)  # Transpose the mel filterbank array

    # Take logarithm
    log_energies = np.log10(mel_energies)

    # Apply DCT
    mfcc_coefficients = next(dct(log_energies))[:13]  # Take the first 13 coefficients

    yield mfcc_coefficients


with wave.open("recording_1s.wav") as w:
    # Get the audio file parameters
    sample_width = w.getsampwidth()
    num_frames = w.getnframes()

    # Read all frames from the WAV file
    audio_data = w.readframes(num_frames)

sample_rate = 44100
hop_size = 10  # ms
FFT_size = 512


# Audio Framing
def frame_audio(audio, FFT_size=512, hop_size=10, sample_rate=44100):
    # hop_size in ms
    frame_len = int(sample_rate * hop_size / 1000)
    frame_num = int((len(audio) - FFT_size) / frame_len) + 1
    print(len(audio))
    print(frame_len, frame_num)

    for n in range(frame_num):
        yield np.array(audio[n * frame_len:n * frame_len + FFT_size], dtype=np.float)


audio_framed = frame_audio(audio_data, FFT_size=FFT_size, hop_size=hop_size, sample_rate=sample_rate)
print(audio_framed)

for n, frame in enumerate(audio_framed):
    # Apply Hamming window
    hamming = hamming_window(len(frame))
    frame *= hamming

    # Compute FFT
    fft_result, b = np.fft.fft(frame)
    magnitude_spectrum = abs(fft_result)

    # Compute power spectrum
    power_spectrum = magnitude_spectrum ** 2

    # Apply Mel filterbank
    mel_filterbank_arr = mel_filterbank()
    print(mel_filterbank_arr.transpose())
    mel_energies = np.dot(power_spectrum, mel_filterbank_arr.transpose())  # Transpose the mel filterbank array

    # Take logarithm
    log_energies = np.log10(mel_energies)

    # Apply DCT
    mfcc_coefficients = next(dct(log_energies))[:13]  # Take the first 13 coefficients

    print(mfcc_coefficients)

