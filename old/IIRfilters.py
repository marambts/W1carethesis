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





        
    
