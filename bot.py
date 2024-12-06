from binance import Client
from binance import BinanceSocketManager
import pandas as pd
import time
import config
import asyncio
from pandas_ta import ema, rsi
import sqlalchemy

# Parameters
SYMBOL = "BTCUSDT"
AT_RISK = 0.1  # Position sizing amount willing to invest

SHORT_EMA_PERIOD = 5 
LONG_EMA_PERIOD = 20
RSI_PERIOD = 14
RSI_LOW_THRES = 50
RSI_UPPER_THRES = 50

# Binance Testnet API keys
api_key = config.tn_api_key
api_secret = config.tn_api_secret

# Initialize Binanceclient
client = Client(api_key, api_secret, testnet=True)
client.https_proxy = None   # a proxy is required without this line

# Log of trades made by the bot
engine = sqlalchemy.create_engine("sqlite:///trading_log.db")
trade_history = pd.DataFrame(columns = ["action", "symbol", "quantity", "price", "timestamp"])

class Position:
    def __init__(self, starting_balance):
        self.starting_balance = starting_balance
        self.balance = starting_balance

        self.qty_invested = 0
        self.last_buy_price = None
        self.data = pd.DataFrame(columns=["timestamp", "price"])

def get_balance(asset):
    balance = client.get_asset_balance(asset=asset)
    return float(balance['free'])

def get_current_price(symbol):
    ticker = client.get_symbol_ticker(symbol=symbol)
    return float(ticker["price"])

def buy(symbol, quantity):
    try:
        order = client.order_market_buy(symbol=symbol, quantity=quantity)
        print(f"Bought {quantity} {symbol} successfully.")
        log_trade("buy", symbol, quantity, order["fills"][0]["price"])
        return order
    except Exception as e:
        print(f"Error placing buy order: {e}")
        return None

def sell(symbol, quantity):
    try:
        order = client.order_market_sell(symbol=symbol, quantity=quantity)
        print(f"Sold {quantity} {symbol} successfully.")
        log_trade("sell", symbol, quantity, order["fills"][0]["price"])
        return order
    except Exception as e:
        print(f"Error placing sell order: {e}")
        return None

def log_trade(action, symbol, quantity, price):
    trade = {
        "action": action,
        "symbol": symbol,
        "quantity": quantity,
        "price": float(price),
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
    }
    trade_history.loc[len(trade_history)] = trade
    trade_history.to_sql('Trades', engine, if_exists='append', index=False)
    print(f"Trade Logged: {trade}")

# Calculate EMA and RSI, and make trading decisions.
def process_indicators(position):
    if len(position.data) < LONG_EMA_PERIOD:  # Not enough data for calculations
        return

    prices = position.data["price"]

    short_ema = ema(prices, length = SHORT_EMA_PERIOD)
    long_ema = ema(prices, length=LONG_EMA_PERIOD)
    relative_strength = rsi(prices, length=RSI_PERIOD)

    print((short_ema.iloc[-1] - long_ema.iloc[-1]), relative_strength.iloc[-1])

    # Process indicators
    # If no stock on hand and there is a buy signal
    if position.qty_invested == 0 and short_ema.iloc[-1] > long_ema.iloc[-1] and relative_strength.iloc[-1] < RSI_LOW_THRES:
        quantity = round(AT_RISK * position.balance / prices.iloc[-1], 4)
        price = float(buy(SYMBOL, quantity)["fills"][0]["price"])

        # amend position
        position.qty_invested += quantity
        position.balance -= quantity * price
        return "buy"

    # If there is stock to sell and there is a sell signal
    elif position.qty_invested > 0 and short_ema.iloc[-1] < long_ema.iloc[-1] and relative_strength.iloc[-1] > RSI_UPPER_THRES:
        price = float(sell(SYMBOL, position.qty_invested))
        
        # amend position
        position.balance += position.qty_invested * price
        position.qty_invested = 0
        return "sell"

# Process incoming trades from Binance
async def process_trade_message(position, msg):
    if msg.get("e") == "trade":
        # Extract trade price and timestamp, currently doing nothing with timestamp
        trade_time = pd.to_datetime(msg["T"], unit="ms")
        trade_price = float(msg["p"])

        # Append new data to the DataFrame
        new_row = {"timestamp": trade_time, "price": trade_price}
        print(new_row)
        position.data.loc[len(position.data)] = new_row

        # Keep only the last 100 rows (rolling window)
        if len(position.data) > 100:
            position.data = position.data.tail(100)

        if process_indicators(position) == "sell":
            roi = (position.balance - position.starting_balance) / position.starting_balance * 100
            print(f"Total Balance: {position.current_balance:.2f} USDT, ROI: {roi:.2f}%")


# Main function
async def run_bot():
    print("Starting bot...")

    position = Position(get_balance('USDT'))

    # Create a trade socket for the symbol for real-time prices
    bsm = BinanceSocketManager(client=client)
    socket = bsm.trade_socket(SYMBOL)

    async with socket as trade_socket:
        print("Connected to Binance Server")
        # infinite loop that checks for signal and potentially executes trade upon receival of a packet
        while True:
            msg = await trade_socket.recv()
            await process_trade_message(position, msg)

# # Main Trading Loop
# def run_bot():
#     """Run the bot continuously."""
#     print("Starting trading bot on Binance Testnet...")
#     starting_balance = get_balance("USDT") + get_balance("BTC") * get_current_price("BTCUSDT")

#     while True:
#         try:
#             # Analyze market
#             signal = analyze_market(symbol)

#             # Fetch balances
#             usdt_balance = get_balance("USDT")
#             btc_balance = get_balance("BTC")
#             current_price = get_current_price(symbol)

#             # Take action based on signal
#             if signal == "buy" and usdt_balance >= trade_quantity * current_price:
#                 buy(symbol, trade_quantity)
#             elif signal == "sell" and btc_balance >= trade_quantity:
#                 sell(symbol, trade_quantity)
#             else:
#                 print("No action taken.")

#             # Calculate ROI periodically
#             calculate_roi(starting_balance)

#             # Wait before the next iteration
#             time.sleep(60)  # Run every 1 minute
#         except Exception as e:
#             print(f"Error in bot execution: {e}")
#             time.sleep(60)  # Wait before retrying



# Start the bot
if __name__ == "__main__":
    asyncio.run(run_bot())    