num_filters = 26
sample_rate = 441000
filter_bank = [[] for _ in range(num_filters)]  # Initialize filter_bank with empty lists

for i in range(num_filters):
    for j in range(sample_rate // 2):
        freq = j / sample_rate
        if freq >= (i * 1000 / 700) and freq <= ((i + 2) * 1000 / 700):
            filter_bank[i].append((freq - i * 1000 / 700) / (1000 / 700))
        elif freq >= ((i + 1) * 1000 / 700) and freq <= ((i + 3) * 1000 / 700):
            filter_bank[i].append(((i + 3) * 1000 / 700 - freq) / (1000 / 700))
        else:
            filter_bank[i].append(0)

print(filter_bank)