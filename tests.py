MA = {'ETH': [30, 100], 'LUNA': [10, 200], 'SOL': [40, 80]}
COIN = 'LUNA'

for k, v in MA.items():
    if COIN == k:
        print(v[0], v[1])