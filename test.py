from main import *

def create_InlineKeyboard(keys: list, index:int=1):
    keyboard = types.InlineKeyboardMarkup()
    callback_button_back = types.InlineKeyboardButton(text='<', callback_data=f'back|{len(keys)}|{index}')
    callback_button_ahead = types.InlineKeyboardButton(text='>', callback_data=f'ahead|{len(keys)}|{index}')
    callback_button_first = types.InlineKeyboardButton(text='1', callback_data=f'1|{len(keys)}')
    callback_button_last = types.InlineKeyboardButton(text=f'{math.ceil(len(keys)/15)}', callback_data=f'{math.ceil(len(keys)/15)}|{len(keys)}')
    keyboard.row(callback_button_back, callback_button_first)
    if math.ceil(len(keys)/15) <= 5:  # (1-60)
        for i in range(1, math.ceil(len(keys)/15)):
            print(f'now key is {i+1}')
            key = types.InlineKeyboardButton(text=str(i+1), callback_data=f'{i+1}|{len(keys)}')
            keyboard.insert(key)
        keyboard.insert(callback_button_ahead)

    return keyboard


async def get_top_coin_cmc(message: types.Message):
    text = message.text[4:]
    text = re.sub(r' *_*-*', '', text)  # delete all '_', '-' and ' ' symbols
    text = int(text)-1 % 200+1 if text.isdigit() else 100

    with open('coin_price.json', 'r') as f:
        prices = json.load(f)
        if time.time() - prices['time'] > 5:
            prices = get_top_cryptocurrencies(text)  # {'ETH': 2000.009, 'BTC': 4000.12, 'DOGE': 0.1093} 

    response = f'Top {text}(1-15) cryptocurrencies:\n' if text in range(16) else f'Top {text} cryptocurrencies:\n'
    keys = list(prices.keys())[1:]  # prices['time'] delete
    for i in range(15):
        if i in range(len(keys)):
            response += f'{keys[i]}: {round(prices[keys[i]], 4)}$\n'

    if text in range(16):
        await bot.send_message(message.from_user.id, text=response)
    else:
        keyboard = create_InlineKeyboard(keys=keys)
        await bot.send_message(message.from_user.id, text=response, reply_markup=keyboard)



s = 'ahead|58|1'
command, total_amount, *index = s.split('|')
print(command, end='---------------\n')
print(total_amount, end='---------------\n')
print(int(index[0]), end='---------------\n')

