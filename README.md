## Binance Trading Bot

A pet project I'm working on that might end up bringing some $$ ...or drain my pockets. It's an automated cryptocurrency trading bot operating through Binance.

It's currently a working prototype that trades a single symbol and exposes a certain percentage of one's capital to risk. It fetches real-time data through websockets which I suppose lends itself to a scalping strategy: its currently operating on an EMA Crossover + RSI strategy but I plan to play around with that in the future. All trades are logged and appended to the SQLite database `trading_log.db` in case I want to perform any kind of analysis on them in the future.


### Setup
The dependencies are listed in `dependencies.txt`, I had some issues with `pandas_ta` and numpy2, so just note that you might have to install the developer version from the `pandas_ta` github. API keys should be updated in `config.py`.

Parameters for the symbol traded, strategy thresholds, and risk limits are adjustable at the top of `bot.py`. If paper trading, set `PAPER_TRADING` to `True` and ensure testnet keys are filled in the config file.

To start just run `python3 bot.py`. Do note that `config.py` and `trading_log.db` need to be in the same directory as `bot.py`.
