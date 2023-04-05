# ************************
#
import machine
import time
import math
import utime

# I2S sensor initializations
import os
from machine import I2S
from machine import Pin\
# ESP32
sck_pin = Pin(2)   # Serial clock output
ws_pin = Pin(15)    # Word clock output
sd_pin = Pin(13)    # Serial data output
I2S_ID = 2

RECORD_TIME_IN_SECONDS = 10
SAMPLE_RATE_IN_HZ = 48000



#======= USER CONFIGURATION =======

WAV_SAMPLE_SIZE_IN_BITS = 32
WAV_SAMPLE_SIZE_IN_BYTES = WAV_SAMPLE_SIZE_IN_BITS // 8
MIC_SAMPLE_BUFFER_SIZE_IN_BYTES = 4096
SDCARD_SAMPLE_BUFFER_SIZE_IN_BYTES = MIC_SAMPLE_BUFFER_SIZE_IN_BYTES // 2 # why divide by 2? only using 16-bits of 32-bit samples
NUM_SAMPLE_BYTES_TO_WRITE = RECORD_TIME_IN_SECONDS * SAMPLE_RATE_IN_HZ * WAV_SAMPLE_SIZE_IN_BYTES
NUM_SAMPLES_IN_DMA_BUFFER = 320
NUM_CHANNELS = 1

# ************************
# snip_16_mono():  snip 16-bit samples from a 32-bit mono sample stream
# assumption: I2S configuration for mono microphone.  e.g. I2S channelformat = ONLY_LEFT or ONLY_RIGHT
# example snip:
#   samples_in[] =  [0x44, 0x55, 0xAB, 0x77, 0x99, 0xBB, 0x11, 0x22]
#   samples_out[] = [0xAB, 0x77, 0x11, 0x22]
#   notes:
#       samples_in[] arranged in little endian format:
#           0x77 is the most significant byte of the 32-bit sample
#           0x44 is the least significant byte of the 32-bit sample
#
# returns:  number of bytes snipped
def snip_16_mono(samples_in, samples_out):
    num_samples = len(samples_in) // 4
    for i in range(num_samples):
        samples_out[2*i] = samples_in[4*i + 2]
        samples_out[2*i + 1] = samples_in[4*i + 3]

    return num_samples * 2

def create_wav_header(sampleRate, bitsPerSample, num_channels, num_samples):
    datasize = num_samples * num_channels * bitsPerSample // 8
    o = bytes("RIFF",'ascii')                                                   # (4byte) Marks file as RIFF
    o += (datasize + 36).to_bytes(4,'little')                                   # (4byte) File size in bytes excluding this and RIFF marker
    o += bytes("WAVE",'ascii')                                                  # (4byte) File type
    o += bytes("fmt ",'ascii')                                                  # (4byte) Format Chunk Marker
    o += (32).to_bytes(4,'little')                                              # (4byte) Length of above format data
    o += (1).to_bytes(2,'little')                                               # (2byte) Format type (1 - PCM)
    o += (num_channels).to_bytes(2,'little')                                    # (2byte)
    o += (sampleRate).to_bytes(4,'little')                                      # (4byte)
    o += (sampleRate * num_channels * bitsPerSample // 8).to_bytes(4,'little')  # (4byte)
    o += (num_channels * bitsPerSample // 8).to_bytes(2,'little')               # (2byte)
    o += (bitsPerSample).to_bytes(2,'little')                                   # (2byte)
    o += bytes("data",'ascii')                                                  # (4byte) Data Chunk Marker
    o += (datasize).to_bytes(4,'little')                                        # (4byte) Data size in bytes
    return o



audio_in = I2S(0,
               sck=sck_pin,
               ws=ws_pin,
               sd=sd_pin,
               mode=I2S.RX,
               bits=32,
               format=I2S.MONO,
               rate=48000,
               ibuf=48000
               )

wav = open('mic_left_channel.wav','wb')


# create header for WAV file and write to SD card
wav_header = create_wav_header(
    SAMPLE_RATE_IN_HZ,
    WAV_SAMPLE_SIZE_IN_BITS,
    NUM_CHANNELS,
    SAMPLE_RATE_IN_HZ * RECORD_TIME_IN_SECONDS
)
num_bytes_written = wav.write(wav_header)

# allocate sample arrays
#   memoryview used to reduce heap allocation in while loop

#6  second buffer
mic_samples = bytearray(6400)
mic_samples_mv = memoryview(mic_samples)

num_sample_bytes_written_to_wav = 0

print('Starting')
# read 32-bit samples from I2S microphone, snip upper 16-bits, write snipped samples to WAV file
while num_sample_bytes_written_to_wav < 192000:
    try:
        num_bytes_read_from_mic = audio_in.readinto(mic_samples_mv)
        if num_bytes_read_from_mic > 0:
            # snip upper 16-bits from each 32-bit microphone sample
            print('%d sample bytes read from i2s' % num_bytes_read_from_mic)
            num_bytes_written = wav.write(mic_samples_mv[:num_bytes_read_from_mic])

            num_sample_bytes_written_to_wav += num_bytes_written
    except (KeyboardInterrupt, Exception) as e:
        print('caught exception {} {}'.format(type(e).__name__, e))
        break


wav.close()

audio_in.deinit()

print('%d sample bytes written to WAV file' % num_sample_bytes_written_to_wav)
print('Done')


#IIR Filters

class SOS_Coefficients:
    def __init__(self):
        self.b1 = 0.0
        self.b2 = 0.0
        self.a1 = 0.0
        self.a2 = 0.0
        
#Delay state  store the state of a second-order section (SOS) Infinite Impulse Response (IIR) filter.
#The w0 and w1 variables represent the current and previous state values of the SOS filter, respectively.
class SOS_Delay_State:
    def __init__(self):
        self.w0 = 0.0
        self.w1 = 0.0


#import machine

def sos_filter_f32(input, output, len, coeffs, w):
    __asm__(
  ".text                    \n"
  ".align  4                \n"
  ".global sos_filter_f32   \n"
  ".type   sos_filter_f32,@function\n"
  "sos_filter_f32:          \n"
  "  entry   a1, 16         \n"
  "  lsi     f0, a5, 0      \n" # float f0 = coeffs.b1;
  "  lsi     f1, a5, 4      \n" # float f1 = coeffs.b2;
  "  lsi     f2, a5, 8      \n" # float f2 = coeffs.a1;
  "  lsi     f3, a5, 12     \n" # float f3 = coeffs.a2;
  "  lsi     f4, a6, 0      \n" # float f4 = w[0];
  "  lsi     f5, a6, 4      \n" # float f5 = w[1];
  "  loopnez a4, 1f         \n" # for (; len>0; len--) { 
  "    lsip    f6, a2, 4    \n" #   float f6 = *input++;
  "    madd.s  f6, f2, f4   \n" #   f6 += f2 * f4; // coeffs.a1 * w0
  "    madd.s  f6, f3, f5   \n" #   f6 += f3 * f5; // coeffs.a2 * w1
  "    mov.s   f7, f6       \n" #   f7 = f6; // b0 assumed 1.0
  "    madd.s  f7, f0, f4   \n" #   f7 += f0 * f4; // coeffs.b1 * w0
  "    madd.s  f7, f1, f5   \n" #   f7 += f1 * f5; // coeffs.b2 * w1 -> result
  "    ssip    f7, a3, 4    \n" #   *output++ = f7;
  "    mov.s   f5, f4       \n" #   f5 = f4; // w1 = w0
  "    mov.s   f4, f6       \n" #   f4 = f6; // w0 = f6
  "  1:                     \n" # }
  "  ssi     f4, a6, 0      \n" # w[0] = f4;
  "  ssi     f5, a6, 4      \n" # w[1] = f5;
  "  movi.n   a2, 0         \n" # return 0;
  "  retw.n                 \n"
    ) 
    
    
    
def sos_filter_sum_sqr_f32(input, output, len, coeffs, w, gain):
    __asm__ (
  ".text                    \n"
  ".align  4                \n"
  ".global sos_filter_sum_sqr_f32 \n"
  ".type   sos_filter_sum_sqr_f32,@function \n"
  "sos_filter_sum_sqr_f32:  \n"
  "  entry   a1, 16         \n" 
  "  lsi     f0, a5, 0      \n"  # float f0 = coeffs.b1;
  "  lsi     f1, a5, 4      \n"  # float f1 = coeffs.b2;
  "  lsi     f2, a5, 8      \n"  # float f2 = coeffs.a1;
  "  lsi     f3, a5, 12     \n"  # float f3 = coeffs.a2;
  "  lsi     f4, a6, 0      \n"  # float f4 = w[0];
  "  lsi     f5, a6, 4      \n"  # float f5 = w[1];
  "  wfr     f6, a7         \n"  # float f6 = gain;
  "  const.s f10, 0         \n"  # float sum_sqr = 0;
  "  loopnez a4, 1f         \n"  # for (; len>0; len--) {
  "    lsip    f7, a2, 4    \n"  #   float f7 = *input++;
  "    madd.s  f7, f2, f4   \n"  #   f7 += f2 * f4; // coeffs.a1 * w0
  "    madd.s  f7, f3, f5   \n"  #   f7 += f3 * f5; // coeffs.a2 * w1;
  "    mov.s   f8, f7       \n"  #   f8 = f7; // b0 assumed 1.0
  "    madd.s  f8, f0, f4   \n"  #   f8 += f0 * f4; // coeffs.b1 * w0;
  "    madd.s  f8, f1, f5   \n"  #   f8 += f1 * f5; // coeffs.b2 * w1; 
  "    mul.s   f9, f8, f6   \n"  #   f9 = f8 * f6;  // f8 * gain -> result
  "    ssip    f9, a3, 4    \n"  #   *output++ = f9;
  "    mov.s   f5, f4       \n"  #   f5 = f4; // w1 = w0
  "    mov.s   f4, f7       \n"  #   f4 = f7; // w0 = f7;
  "    madd.s  f10, f9, f9  \n"  #   f10 += f9 * f9; // sum_sqr += f9 * f9;
  "  1:                     \n"  # }
  "  ssi     f4, a6, 0      \n"  # w[0] = f4;
  "  ssi     f5, a6, 4      \n"  # w[1] = f5;
  "  rfr     a2, f10        \n"  # return sum_sqr; 
  "  retw.n                 \n"  # 
    )


class SOS_IIR_Filter:
    def __init__(self, num_sos=None, gain=None, sos=None):
        self.num_sos = num_sos
        self.gain = gain
        self.sos = None
        self.w = None

        if num_sos is not None and gain is not None:
            self.num_sos = num_sos
            self.gain = gain
            if num_sos > 0:
                self.sos = [SOS_Coefficients() for i in range(num_sos)]
                if sos is not None:
                    for i in range(num_sos):
                        self.sos[i] = sos[i]
                self.w = [SOS_Delay_State() for i in range(num_sos)]

    def from_array(self, gain, sos):
        self.num_sos = len(sos)
        self.gain = gain
        if self.num_sos > 0:
            self.sos = [SOS_Coefficients() for i in range(self.num_sos)]
            for i in range(self.num_sos):
                self.sos[i] = sos[i]
            self.w = [SOS_Delay_State() for i in range(self.num_sos)]


    def filter(self, input, output, len):
        if self.num_sos < 1 or self.sos is None or self.w is None:
            return 0.0
        source = input
    # Apply all but last Second-Order-Section
        for i in range(self.num_sos - 1):
            sos_filter_f32(source, output, len, self.sos[i * 6:(i + 1) * 6], self.w[i * 4:(i + 1) * 4])
            source = output
    # Apply last SOS with gain and return the sum of squares of all samples
        return sos_filter_sum_sqr_f32(source, output, len, self.sos[(self.num_sos - 1) * 6:], self.w[(self.num_sos - 1) * 4:], self.gain)

    def __del__(self):
        self.w = None
        self.sos = None



#DC Blocker
dc_coeffs = SOS_Coefficients()
dc_coeffs.b1 = -1.0
dc_coeffs.b2 = 0.0
dc_coeffs.a1 = 0.9992
dc_coeffs.a2 = 0.0

#DC_Blocker_Filter = SOS_IIR_Filter(num_sos=4, gain=1.0, sos=[dc_coeffs.b1, dc_coeffs.b2, dc_coeffs.a1, dc_coeffs.a2])
def DC_Blocker_Filter(input_signal, num_sos=1, gain=1, sos=[dc_coeffs.b1, dc_coeffs.b2, dc_coeffs.a1, dc_coeffs.a2]):
    # Create an instance of the SOS_IIR_Filter class with the given parameters
    dc_iir_filter = SOS_IIR_Filter(num_sos=num_sos, gain=gain, sos=sos)

    # Filter the input signal using the IIR filter
    dc_output_signal = dc_iir_filter.filter(input_signal)

    # Return the filtered signal
    return dc_output_signal


#INMP441 Equalizer
eq_coeffs = SOS_Coefficients()
eq_coeffs.b1 = -2.00026996133106
eq_coeffs.b2 = +1.00027056142719
eq_coeffs.a1 = -1.060868438509278
eq_coeffs.a2 = -0.163987445885926

def INMP_Equalizer_Filter(input_signal, num_sos=1, gain=1.00197834654696, sos=[eq_coeffs.b1, eq_coeffs.b2, eq_coeffs.a1, eq_coeffs.a2]):
    # Create an instance of the SOS_IIR_Filter class with the given parameters
    eq_iir_filter = SOS_IIR_Filter(num_sos=num_sos, gain=gain, sos=sos)

    # Filter the input signal using the IIR filter
    eq_output_signal = eq_iir_filter.filter(input_signal)

    # Return the filtered signal
    return eq_output_signal



#A Weighting 
weight_coeffs = SOS_Coefficients()
weight_coeffs.b1 = -1.986920458344451
weight_coeffs.b2 = +0.986963226946616
weight_coeffs.a1 = +1.995178510504166
weight_coeffs.a2 = -0.995184322194091

def AWeight_Filter(input_signal, num_sos=3, gain= 0.16999494814743, sos=[[-2.00026996133106, +1.00027056142719, -1.060868438509278, -0.163987445885926], [+4.35912384203144, +3.09120265783884, +1.208419926363593, -0.273166998428332], [-0.70930303489759, -0.29071868393580, +1.982242159753048, -0.982298594928989]]):
    # Create an instance of the SOS_IIR_Filter class with the given parameters
    a_iir_filter = SOS_IIR_Filter(num_sos=num_sos, gain=gain, sos=sos)

    # Filter the input signal using the IIR filter
    a_output_signal = a_iir_filter.filter(input_signal)

    # Return the filtered signal
    return a_output_signal

SAMPLE_RATE = 48000  # Hz, fixed to design of IIR filters
SAMPLE_BITS = 32    # bits
SAMPLE_T = int       #MicroPython does not have int32_t, not sure if this is the proper alternative
SAMPLES_SHORT = int(SAMPLE_RATE/8)  # ~125ms
LEQ_PERIOD = 1 #seconds (s)
SAMPLES_LEQ = SAMPLE_RATE * LEQ_PERIOD
DMA_BANK_SIZE = SAMPLES_SHORT / 16
DMA_BANKS = 32

# Data we push to 'samples_queue'

class sum_queue_t:
    def __init__(self):
        # Sum of squares of mic samples, after Equalizer filter
        self.sum_sqr_SPL = 0.0
        # Sum of squares of weighted mic samples
        self.sum_sqr_weighted = 0.0
        # Debug only, FreeRTOS ticks we spent processing the I2S data
        self.proc_ticks = 0

samples_queue = []
 
# Static buffer for block of samples

import array

samples = array.array('f', [0.0] * SAMPLES_SHORT)

# I2S Microphone sampling setup 

def mic_i2s_init():
    i2s_config = {
        "mode": (I2S_MODE_MASTER | I2S_MODE_RX),
        "sample_rate": SAMPLE_RATE,
        "bits_per_sample": SAMPLE_BITS,
        "channel_format": I2S_CHANNEL_FMT_ONLY_LEFT,
        "communication_format": (I2S_COMM_FORMAT_I2S | I2S_COMM_FORMAT_I2S_MSB),
        "intr_alloc_flags": ESP_INTR_FLAG_LEVEL1,
        "dma_buf_count": DMA_BANKS,
        "dma_buf_len": DMA_BANK_SIZE,
        "use_apll": True,
        "tx_desc_auto_clear": False,
        "fixed_mclk": 0
    }
    # I2S pin mapping
    pin_config = {
        "bck_io_num": I2S_SCK,
        "ws_io_num": I2S_WS,
        "data_out_num": None,
        "data_in_num": I2S_SD
    }

    i2s_driver_install(I2S_PORT, i2s_config, 0, None)


    i2s_set_pin(I2S_PORT, pin_config)
    

I2S_TASK_PRI = 4
I2S_TASK_STACK = 2048

def mic_i2s_reader_task():
    mic_i2s_init()

    # Discard first block, microphone may have startup time (i.e. INMP441 up to 83ms)
    bytes_read = 0
    i2s_read(I2S_PORT, samples, SAMPLES_SHORT * 4, bytes_read, portMAX_DELAY)
    # reads audio data from the I2S bus and stores it in the buffer 'samples'
    # samples: The buffer to store the audio data. This buffer must be pre-allocated with a size of SAMPLES_SHORT * 4 bytes, 
    # where SAMPLES_SHORT is the number of audio samples to read. Each audio sample is 4 bytes (32 bits) long.
    
    while True:
        # Block and wait for microphone values from I2S
        #
        # Data is moved from DMA buffers to our 'samples' buffer by the driver ISR
        # and when there is requested ammount of data, task is unblocked
        #
        # Note: i2s_read does not care it is writing in float[] buffer, it will write
        #       integer values to the given address, as received from the hardware peripheral.
        i2s_read(I2S_PORT, samples, SAMPLES_SHORT * 4, bytes_read, portMAX_DELAY)

        start_tick = ticks_ms()

        # Convert (including shifting) integer microphone values to floats,
        # using the same buffer (assumed sample size is same as size of float),
        # to save a bit of memory
        int_samples = array.array("i", samples)
        for i in range(SAMPLES_SHORT):
            samples[i] = MIC_CONVERT(int_samples[i])

        q = {}
        # Apply equalization and calculate Z-weighted sum of squares,
        # writes filtered samples back to the same buffer.
        q['sum_sqr_SPL'] = MIC_EQUALIZER.filter(samples, samples, SAMPLES_SHORT)

        # Apply weighting and calucate weigthed sum of squares
        q['sum_sqr_weighted'] = WEIGHTING.filter(samples, samples, SAMPLES_SHORT)

        # Debug only. Ticks we spent filtering and summing block of I2S data
        q['proc_ticks'] = ticks_ms() - start_tick

        # Send the sums to FreeRTOS queue where main task will pick them up
        # and further calcualte decibel values (division, logarithms, etc...)
        xQueueSend(samples_queue, q, portMAX_DELAY)
        
def setup():
    # If needed, now you can actually lower the CPU frequency,
    # i.e. if you want to (slightly) reduce ESP32 power consumption
    setCpuFrequencyMhz(80) # It should run as low as 80MHz
    uart = UART(0, 115200)
    time.sleep(1) # Safety

    # Create FreeRTOS queue
    samples_queue = xQueueCreate(8, sizeof(sum_queue_t))

    # Create the I2S reader FreeRTOS task
    # NOTE: Current version of ESP-IDF will pin the task
    # automatically to the first core it happens to run on
    # (due to using the hardware FPU instructions).
    # For manual control see: xTaskCreatePinnedToCore
    mic_i2s_reader_task_handle = _thread.start_new_thread(mic_i2s_reader_task, (None,))

    q = sum_queue_t()
    Leq_samples = 0
    Leq_sum_sqr = 0
    Leq_dB = 0

    # Read sum of samples, calculated by 'mic_i2s_reader_task'
    while True:
        if xQueueReceive(samples_queue, q, portMAX_DELAY):
            # Calculate dB values relative to MIC_REF_AMPL and adjust for microphone reference
            short_RMS = sqrt(q.sum_sqr_SPL / SAMPLES_SHORT)
            short_SPL_dB = MIC_OFFSET_DB + MIC_REF_DB + 20 * log10(short_RMS / MIC_REF_AMPL)

            # In case of acoustic overload or below noise floor measurement, report infinity Leq value
            if short_SPL_dB > MIC_OVERLOAD_DB:
                Leq_sum_sqr = INFINITY
            elif math.isnan(short_SPL_dB) or (short_SPL_dB < MIC_NOISE_DB):
                Leq_sum_sqr = -INFINITY

            # Accumulate Leq sum
            Leq_sum_sqr += q.sum_sqr_weighted
            Leq_samples += SAMPLES_SHORT

            # When we gather enough samples, calculate new Leq value
            if Leq_samples >= SAMPLE_RATE * LEQ_PERIOD:
                Leq_RMS = sqrt(Leq_sum_sqr / Leq_samples)
                Leq_dB = MIC_OFFSET_DB + MIC_REF_DB + 20 * log10(Leq_RMS / MIC_REF_AMPL)
                Leq_sum_sqr = 0
                Leq_samples = 0

                print("{:.1f} dBA".format(Leq_dB))
