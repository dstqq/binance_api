from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from coinmarketcapapi import CoinMarketCapAPI, CoinMarketCapAPIError
from binance.spot import Spot
from binance.lib.utils import config_logging
from binance.error import ClientError

from cfg import api_key, api_secret, token, admin, coinmarketcap_api

import re
import time
import json
import logging
import math


bot = Bot(token=token, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot)

zeros_list = ["0.00000000", "0.00", "0.0", "0"]
DEBAG = True

client = Spot(key=api_key, secret=api_secret)
logger = logging.getLogger(__name__)


def hashrate_round(value: str) -> int:
    s = int(value.split('.')[0])
    return round(s/1000000, 2)


def cryptocurrency_round(value: str):
    s = float(value)
    return round(s, 2)


def create_InlineKeyboard(keys: list, index=1):
    keyboard = types.InlineKeyboardMarkup()
    callback_button_back = types.InlineKeyboardButton(text='<', callback_data=f'back|{len(keys)}|{index}')
    callback_button_ahead = types.InlineKeyboardButton(text='>', callback_data=f'ahead|{len(keys)}|{index}')
    callback_button_first = types.InlineKeyboardButton(text='1', callback_data=f'1|{len(keys)}')
    keyboard.row(callback_button_back, callback_button_first)
    if math.ceil(len(keys)/15) <= 5:  # (1-75)
        for i in range(1, math.ceil(len(keys)/15)):
            key = types.InlineKeyboardButton(text=str(i+1), callback_data=f'{i+1}|{len(keys)}')
            keyboard.insert(key)
        keyboard.insert(callback_button_ahead)
    else:
        if index in range(1, 4):  # first 3 buttons
            keyboard.insert(types.InlineKeyboardButton(text=f'2', callback_data=f'2|{len(keys)}'))
            keyboard.insert(types.InlineKeyboardButton(text=f'3', callback_data=f'3|{len(keys)}'))
            keyboard.insert(types.InlineKeyboardButton(text=f'4..', callback_data=f'4|{len(keys)}'))
        elif index in range(math.ceil(len(keys)/15)-2, math.ceil(len(keys)/15)+1):  # last 3 buttons
            keyboard.insert(types.InlineKeyboardButton(text=f'..{math.ceil(len(keys)/15)-3}', callback_data=f'{math.ceil(len(keys)/15)-3}|{len(keys)}'))
            keyboard.insert(types.InlineKeyboardButton(text=f'{math.ceil(len(keys)/15)-2}', callback_data=f'{math.ceil(len(keys)/15)-2}|{len(keys)}'))
            keyboard.insert(types.InlineKeyboardButton(text=f'{math.ceil(len(keys)/15)-1}', callback_data=f'{math.ceil(len(keys)/15)-1}|{len(keys)}'))
        else:
            keyboard.insert(types.InlineKeyboardButton(text=f'..{index-1}', callback_data=f'{index-1}|{len(keys)}'))
            keyboard.insert(types.InlineKeyboardButton(text=f'{index}', callback_data=f'{index}|{len(keys)}'))
            keyboard.insert(types.InlineKeyboardButton(text=f'{index+1}..', callback_data=f'{index+1}|{len(keys)}'))
        keyboard.insert(types.InlineKeyboardButton(text=f'{math.ceil(len(keys)/15)}', callback_data=f'{math.ceil(len(keys)/15)}|{len(keys)}'))
        keyboard.insert(callback_button_ahead)
    
    return keyboard


async def get_top_coin_cmc(message: types.Message):
    text = message.text[4:]
    text = re.sub(r' *_*-*', '', text)  # delete all '_', '-' and ' ' symbols
    length = int(text)-1 % 200+1 if text.isdigit() else 100

    with open('coin_price.json', 'r') as f:
        prices = json.load(f)
        if time.time() - prices['time'] > 5:
            prices = get_top_cryptocurrencies()  # {'ETH': 2000.009, 'BTC': 4000.12, 'DOGE': 0.1093} 

    response = f'Top {length}(1-15) cryptocurrencies:\n' if length not in range(16) else f'Top {length} cryptocurrencies:\n'
    keys = list(prices.keys())[1:length+1]  # prices['time'] ignore
    for i in range(15):
        if i in range(len(keys)):
            response += f'{keys[i]}: {round(prices[keys[i]], 4)}$\n'

    if length in range(16):
        await bot.send_message(message.from_user.id, text=response)
    else:
        keyboard = create_InlineKeyboard(keys=keys)
        await bot.send_message(message.from_user.id, text=response, reply_markup=keyboard)


def get_top_cryptocurrencies(len=200) -> dict:
    cmc = CoinMarketCapAPI(coinmarketcap_api)
    r = cmc.cryptocurrency_listings_latest(limit=len)
    prices = {'time': time.time()}
    for cryptocurrency in r.data:
        prices[cryptocurrency["symbol"]] = cryptocurrency["quote"]["USD"]["price"]
    with open('coin_price.json', 'w') as f:
        json.dump(prices, f)
    return prices


# 200 firsts market cap coins
def get_crypto_prices_cmc(assets_count: dict) -> dict:
    cmc = CoinMarketCapAPI(coinmarketcap_api)
    r = cmc.cryptocurrency_listings_latest(limit=200)

    prices = {}
    for key in assets_count.keys():
        for cryptocurrency in r.data:
            if cryptocurrency["symbol"] == key:
                prices[key] = cryptocurrency["quote"]["USD"]["price"]
    return prices


def get_crypto_price_binance(assets_count: dict) -> dict:  # Any coin on Binance
    prices = {}
    for key in assets_count.keys():
        a = client.klines(f"{key}USDT", "1m", limit=1)
        prices[key] = cryptocurrency_round(a[0][1])
    return prices


def get_cryptocurrency_prices(assets_count: dict) -> dict:
    cmc_prices = get_crypto_prices_cmc(assets_count)
    reject_assets = {}
    for assets_key in assets_count.keys():
        if assets_key not in cmc_prices.keys():
            reject_assets[assets_key] = cmc_prices[assets_key]
    binance_prices = get_crypto_price_binance(reject_assets)
    return cmc_prices | binance_prices


def get_spot_account_info():
    jsonchick = client.account()
    total_cost = 0
    spot_balance = ''
    with open('spot_wallet.json', 'w') as f:
        json.dump(jsonchick, f)
    assets_count = {}
    for asset in jsonchick["balances"]:
        if asset["free"] not in zeros_list:
            assets_count[asset['asset']] = asset['free']
    prices = get_crypto_prices_cmc(assets_count)
    for key in assets_count.keys():
        total_cost += prices[key]*float(assets_count[key])
        spot_balance += f"{key} {assets_count[key]} ≈ {round(prices[key]*float(assets_count[key]),2)}$\n"
    spot_balance = f"{time.ctime(int(str(jsonchick['updateTime'])[:10]))}\nEstimated Balance: {round(total_cost, 2)}$\n{'_'*20}\n" + spot_balance
    return spot_balance


def get_mining_info(algo="Ethash", userName="dstqqbmining"):
    mining_stat = client.mining_statistics_list(algo=algo, userName=userName)
    with open('account.json', 'w') as f:
        json.dump(mining_stat, f)
    time_ = client.time()['serverTime']
    fifteenMinHashRate = hashrate_round(mining_stat['data']['fifteenMinHashRate'])
    dayHashRate = hashrate_round(mining_stat['data']['dayHashRate'])
    response = (
        f"{time.ctime(int(str(time_)[:10]))} stats\n"
        f"Hashrate:\n"
        f"15 Minutes  |  24 Hours\n"
        f"{fifteenMinHashRate} MH/s  |  {dayHashRate} MH/s\n"
        f"\nEarnings:\n"
        f"Today's Income  |  Yesterday's Income\n"
        f"{mining_stat['data']['profitToday']['ETH']} ETH  |  {mining_stat['data']['profitYesterday']['ETH']} ETH"
    )
    return response


def mining_coin_list_():  # refrest json file with all minings coins
    coin_list = client.mining_coin_list()
    print(coin_list)
    with open('mining_coin_list.json', 'w') as file:
        json.dump(coin_list, file)


def get_savings_account():
    a = client.savings_account()
    print(a)
    with open('savings_accoun.json', 'w') as file:
        json.dump(a, file)


def get_funding_wallet():  # Кошелек поплнений(Майнинг)
    assets = client.funding_wallet()
    response = 'Funding wallet assets:\n' if assets else ''
    assets_count = {}
    total_cost = 0
    for asset in assets:
        assets_count[asset['asset']] = asset['free']

    prices = get_cryptocurrency_prices(assets_count)
    for key in assets_count.keys():
        total_cost += prices[key]*float(assets_count[key])
        response += f"{key} {assets_count[key]} ≈ {round(prices[key]*float(assets_count[key]),2)}$\n"

    with open('funding_wallet.json', 'w') as file:
        json.dump(assets, file)
    response = f"Estimated Balance: {round(total_cost, 2)}$\n{'_'*15}\n" + response
    return response


def get_account_snapshot():
    status = client.account_snapshot(type='SPOT', limit=9)
    with open('account_status.json', 'w') as file:
        json.dump(status, file)


@dp.callback_query_handler()  # lambda c: c.data == 'a1'
async def on_first_button_first_answer(callback_query: types.CallbackQuery):
    command, total_amount, *index = callback_query.data.split('|')  # ['ahead', '100', '1'] -> command, total_amount, index
    total_amount = int(total_amount)
    if command == 'ahead':
        index = int(index[0]) % math.ceil(total_amount/15) + 1
    elif command == 'back':
        index = (int(index[0])-2) % math.ceil(total_amount/15) + 1
    else:
        index = int(command)

    response = f'Top {total_amount}({15*(index-1)+1}-{15*index if 15*index < total_amount else total_amount}) cryptocurrencies:\n'
    with open('coin_price.json', 'r') as f:
        prices = json.load(f)
        keys = list(prices.keys())[1:total_amount+1]  # prices['time'] igonre
    for i in range(15*(index-1), 15*index):
        if i in range(len(keys)):
            response += f'{keys[i]}: {round(prices[keys[i]], 4)}$\n'

    keyboard = create_InlineKeyboard(keys=keys, index=index)
    await bot.edit_message_text(response, callback_query.message.chat.id, callback_query.message.message_id, reply_markup=keyboard)


@dp.message_handler(commands=['mining_stat'])
async def send_mining_stat(message: types.Message):
    if message.from_user.id == admin:
        text = get_mining_info()
        await bot.send_message(message.from_user.id, text=text)


@dp.message_handler(commands=['funding_wallet'])
async def send_funding_wallet(message: types.Message):
    if message.from_user.id == admin:
        text = get_funding_wallet()
        await bot.send_message(message.from_user.id, text=text)


@dp.message_handler(commands=['spot_wallet'])
async def send_spot_wallet(message: types.Message):
    if message.from_user.id == admin:
        text = get_spot_account_info()
        await bot.send_message(message.from_user.id, text=text)


@dp.message_handler(types.Message)
async def text_handler(message: types.Message):
    if message.text.startswith('/top'):
        await get_top_coin_cmc(message)


if __name__ == "__main__":
    # get_spot_account_info()
    # print(get_mining_info())
    # print(get_funding_wallet())
    # get_account_snapshot()
    # get_top_cryptocurrencies(200)
    executor.start_polling(dp, skip_updates=True)
