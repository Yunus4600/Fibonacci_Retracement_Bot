import MetaTrader5 as mt5
import config
from logging_config import logger

def fetch_price_data():
    rates = mt5.copy_rates_from_pos(config.SYMBOL, mt5.TIMEFRAME_M15, 0, 100)
    if rates is not None:
        logger.info(f"Fetched {len(rates)} price data points for {config.SYMBOL}")
    else:
        logger.error("Failed to fetch price data")
    return rates
