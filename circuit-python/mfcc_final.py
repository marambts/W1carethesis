import adafruit_wave as wave
import time
import ulab
from ulab import numpy as np
from ulab import scipy
from ulab import utils


# Audio Framing
def frame_audio(audio, FFT_size=512, hop_size=10, sample_rate=44100):
    # hop_size in ms
    audio_zeros = np.zeros(256, dtype=np.int16)

    frame_len = int(np.ceil((sample_rate * hop_size / 1000)))
    frame_num = int((len(audio) - FFT_size) / frame_len) + 1

    for n in range(frame_num):
        frame_start = n * frame_len
        frame_end = frame_start + FFT_size

        if frame_start < 256:
            frame = np.concatenate((audio_zeros[256 - frame_start:], audio[:frame_end]))
        else:
            frame = audio[frame_start - 256:frame_end]

        yield np.array(frame[:FFT_size], dtype=np.float)


# Hamming window function
def hamming_window(length):
    return 0.54 - 0.46 * np.cos(2 * np.pi * np.arange(length) / (length - 1))


def fastft(frame):
    fft_result = utils.spectrogram(frame)
    magnitude_spectrum = abs(fft_result[:len(fft_result) // 2 + 1])
    return magnitude_spectrum


# Mel Filterbank computation (note that this is fixed for num_filters = 26, fft_size =512, sample_rate = 44100)
def mel_filterbank():
    mel_filterbank = [0, 3, 7, 12, 20, 31, 46, 66, 94, 132, 184, 256]
    mel_freqs = [0., 260.59867204, 618.21401246, 1108.96375691, 1782.4116895, 2706.57338913, 3974.785534, 5715.13253718,
                 8103.38256596, 11380.73943188, 15878.20322216, 22050.]

    filter_points = np.array(mel_filterbank)
    mel_freqs = np.array(mel_freqs)
    return filter_points, mel_freqs


def dct(dct_filter_num, filter_len):
    basis = np.empty((dct_filter_num, filter_len))
    basis[0, :] = 1.0 / np.sqrt(filter_len)

    samples = np.arange(1, 2 * filter_len, 2) * np.pi / (2.0 * filter_len)

    for i in range(1, dct_filter_num):
        basis[i, :] = np.cos(i * samples) * np.sqrt(2.0 / filter_len)

    return basis


def linspace_custom(start, stop, num):
    if num < 2:
        return np.array([start, stop])
    return np.linspace(start, stop, num)


def get_filters(filter_points, FFT_size):
    filters = np.zeros((len(filter_points) - 2, FFT_size // 2 + 1))
    for n in range(len(filter_points) - 2):
        filter_values = np.zeros(FFT_size // 2 + 1)
        filter_values[int(filter_points[n]):int(filter_points[n + 1])] = linspace_custom(0, 1, num=int(
            filter_points[n + 1]) - int(filter_points[n]))
        filter_values[int(filter_points[n + 1]):int(filter_points[n + 2])] = linspace_custom(1, 0, num=int(
            filter_points[n + 2]) - int(filter_points[n + 1]))
        filters[n] = filter_values
    return filters


def multiply_filter_values(filter_generator, enorm_reshaped):
    counter = 0
    for filter_values in filter_generator:
        print(counter)
        filter_values_reshaped = filter_values.reshape((1, filter_values.shape[0]))

        multiplied_values_generator = (x * y for x, y in zip(filter_values_reshaped, enorm_reshaped[counter]))
        counter += 1
        yield multiplied_values_generator


def power_spectrum(audio_framed):
    for n, frame in enumerate(audio_framed):
        hamming = hamming_window(len(frame))
        frame *= hamming

        # Compute FFT
        frame = fastft(frame)
        # print(magnitude_spectrum)

        # Compute power spectrum
        frame = frame ** 2
        yield np.array(frame)


def take_log(power_spectrum):
    for i, frame in enumerate(power_spectrum):
        audio_filtered = np.dot(frame, filters)
        audio_log = 10.0 * np.log10(audio_filtered)
        yield np.array(audio_log)


def cepstral_coefficients(audio_log):
    for i, frame in enumerate(audio_log):
        cepstral_coefficients = np.dot(frame, dct_filters)
        yield cepstral_coefficients


with wave.open("recording_1s.wav") as w:
    # Get the audio file parameters
    sample_width = w.getsampwidth()
    num_frames = w.getnframes()

    # Read all frames from the WAV file
    audio_data = np.frombuffer(w.readframes(num_frames), dtype=np.int16)

sample_rate = 44100
hop_size = 10  # ms
FFT_size = 512
mel_filter_num = 10
dct_filter_num = 13

audio_framed = frame_audio(audio_data, FFT_size=FFT_size, hop_size=hop_size, sample_rate=sample_rate)
power_spectrum = power_spectrum(audio_framed)

# print(audio_framed)
# Apply Mel filterbank
filter_points, mel_freqs = mel_filterbank()
filters = get_filters(filter_points, FFT_size)
enorm = 2.0 / (mel_freqs[2:mel_filter_num + 2] - mel_freqs[:mel_filter_num])
enorm_reshaped = enorm.reshape((enorm.shape[0], 1))
filters *= enorm_reshaped
filters = filters.transpose()
audio_log = take_log(power_spectrum)

dct_filters = dct(dct_filter_num, mel_filter_num)
dct_filters = np.array(dct_filters.transpose())

coeff = list(next(cepstral_coefficients(audio_log)))
print("The 13 Cepstral Coefficients are:", coeff)
