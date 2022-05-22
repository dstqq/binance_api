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


client = Spot(key=api_key, secret=api_secret)
logger = logging.getLogger(__name__)


def hashrate_round(value: str) -> int:
    s = int(value.split('.')[0])
    return round(s/1000000, 2)


def cryptocurrency_round(value: str):
    s = float(value)
    return round(s, 2)

def create_InlineKeyboard(keys: list, ):
    keyboard = types.InlineKeyboardMarkup()
    callback_button_back = types.InlineKeyboardButton(text='<', callback_data='back')
    callback_button_ahead = types.InlineKeyboardButton(text='>', callback_data='ahead')
    callback_button_first = types.InlineKeyboardButton(text='1', callback_data='1')
    callback_button_last = types.InlineKeyboardButton(text=f'{math.ceil(len(keys)/15)}', callback_data=f'{math.ceil(len(keys)/15)}')
    callback_button_second = types.InlineKeyboardButton(text='2', callback_data='2')
    keyboard.row(callback_button_back, callback_button_first, callback_button_last, callback_button_ahead)

    return keyboard


async def get_top_coin_cmc(message: types.Message):
    text = message.text[4:]
    text = re.sub(r' *_*-*', '', text)  # delete all '_', '-' and ' ' symbols
    text = int(text)-1 % 200+1 if text.isdigit() else 100
    prices = get_top_cryptocurrencies(text)

    response = f'Top {text} cryptocurrencies:\n'
    keys = list(prices.keys())
    for i in range(16):
        if i in range(len(keys)):
            response += f'{keys[i]}: {round(prices[keys[i]], 4)}$\n'

    if text in range(16):
        await bot.send_message(message.from_user.id, text=response)
    else:
        keyboard = create_InlineKeyboard(keys=keys)


def get_top_cryptocurrencies(len: int) -> dict:
    cmc = CoinMarketCapAPI(coinmarketcap_api)
    r = cmc.cryptocurrency_listings_latest(limit=len)
    prices = {}
    for cryptocurrency in r.data:
        prices[cryptocurrency["symbol"]] = cryptocurrency["quote"]["USD"]["price"]

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


def get_deposit_adress(coin):
    return client.deposit_address(coin)


def get_saving_account():
    a = client.savings_flexible_products()
    with open('a.json', 'w') as f:
        json.dump(a, f)


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
    # print(get_deposit_adress('BNB'))
    # get_saving_account()
    executor.start_polling(dp, skip_updates=True)
