import MetaTrader5 as mt5
import config
from logging_config import logger

def place_order(entry_price, sl_price, tp_price, trade_type):
    """Place order with fixed lot size and Fibonacci-based stops"""
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": config.SYMBOL,
        "volume": config.LOT_SIZE,  # Using fixed lot size from config
        "type": trade_type,
        "price": entry_price,
        "sl": sl_price,
        "tp": tp_price,
        "deviation": 10,
        "magic": 123456,
        "comment": "Golden Fib Buy",
        "type_filling": mt5.ORDER_FILLING_FOK,
        "type_time": mt5.ORDER_TIME_GTC,
    }

    # Log trade details before execution
    logger.info(f"Placing order: Entry: {entry_price:.5f}, SL: {sl_price:.5f}, TP: {tp_price:.5f}")
    logger.info(
        f"Position Size: {config.LOT_SIZE} lots, R:R Ratio: {abs(tp_price - entry_price) / abs(sl_price - entry_price):.2f}")

    try:
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Order placement failed: {result.comment}")
            return False
        else:
            logger.info(f"Order placed successfully at {entry_price} with lot size {config.LOT_SIZE}")
            logger.info(f"Stop Loss: {sl_price}, Take Profit: {tp_price}")
            return True
    except Exception as e:
        logger.error(f"Error placing order: {str(e)}")
        return False