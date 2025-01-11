import MetaTrader5 as mt5
import strategy
import trade
import fetch_data
import config
from logging_config import logger

def main():
    if not mt5.initialize():
        logger.error("Failed to initialize MT5")
        mt5.shutdown()
        return

    logger.info("Connected to MT5")
    symbol_info = mt5.symbol_info(config.SYMBOL)
    if symbol_info is None:
        logger.error(f"Symbol {config.SYMBOL} not found")
        mt5.shutdown()
        return

    strategy.run_fibonacci_strategy()
    mt5.shutdown()

if __name__ == "__main__":
    main()
