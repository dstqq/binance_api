s = '20580051.56'  # '9544372'
s = int(s.split('.')[0])
print(round(s/1000000, 2))
from http import client
from binance.spot import Spot
import time

client = Spot()
a = 1652486399000
print(a)
print(int(a))
print(time.time())
print(time.ctime(int(str(client.time()['serverTime'])[:10])))

print(float('0.00189685'))