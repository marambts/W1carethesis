import librosa
import soundfile as sf

num_mfccs = 13

audio_path = 'download.wav'
audio, sr = librosa.load(audio_path)

mfccs = librosa.feature.mfcc(y=audio, sr=sr)

print('MFCC:', mfccs)

mfccs_mean = [0] * num_mfccs
for i in range(num_mfccs):
    mfccs_mean[i] = sum([mfccs[j][i] for j in range(len(mfccs))]) / len(mfccs)

print('MFCC mean:', mfccs_mean)

spectrogram = librosa.feature.inverse.mfcc_to_mel(mfccs)

audio = librosa.griffinlim(spectrogram)

output_file = 'reconstructed_lib_audio.wav'
sf.write(output_file, audio, sr)
