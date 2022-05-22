import imp
import re

s = '20580051.56'  # '9544372'
s = int(s.split('.')[0])
print(round(s/1000000, 2))
text = 'sdads'
# if text.startswith(('_', ' ')):
#     print('_______________')

def get_top_coin_cmc(text: str):
    text = re.sub(r' *_*', '', text)  # delete all '_' and ' ' symbols
    text = int(text)-1 % 200+1 if text.isdigit() else 100
    print(text)


di = {'ETH': 2000.009, 'BTC': 4000.12, 'DOGE': 0.1093}
response = ''
key = list(di.keys())
for i in range(0, 5):
    if i in range(len(key)):
        response += f'{key[i]}: {di[key[i]]}\n'
print(response, end=f'\n{"-"*20}\n')
t = 16
import math
print(math.ceil(t/15))