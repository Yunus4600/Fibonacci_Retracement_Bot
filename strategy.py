import MetaTrader5 as mt5
import config
from logging_config import logger
import time
import trade
import pandas as pd



# Previous trend analysis functions remain the same...

def calculate_fibonacci_levels(high, low):
    """Calculate Fibonacci retracement levels with detailed logging"""
    diff = high - low
    levels = [high - diff * level for level in config.FIB_LEVELS]

    # Create detailed level descriptions
    level_desc = {
        0.236: "Shallow retracement",
        0.382: "Moderate retracement",
        0.5: "Midpoint retracement",
        0.618: "Golden ratio (Entry zone)",
        0.786: "Deep retracement"
    }

    # Log each level with its description
    logger.info("\n=== Fibonacci Levels ===")
    for level, price in zip(config.FIB_LEVELS, levels):
        logger.info(f"{level} ({level_desc[level]}): {price:.2f}")

    return levels


def check_entry_conditions(current_price, fib_levels):
    """Enhanced entry condition checking with detailed logging"""
    symbol_info = mt5.symbol_info(config.SYMBOL)
    if symbol_info is None:
        logger.error("Failed to get symbol info")
        return False

    margin = 0.25
    spread = symbol_info.ask - symbol_info.bid

    if spread > 0.5:
        logger.info(f"⚠️ Current spread {spread} too high")
        return False

    # Focus on golden ratio level
    golden_level = fib_levels[3]  # 0.618 level
    distance = abs(current_price - golden_level)

    # Enhanced entry zone analysis
    if distance <= margin:
        logger.info("\n=== Entry Conditions Met ===")
        logger.info(f"Current Price: {current_price:.2f}")
        logger.info(f"Golden Ratio Level: {golden_level:.2f}")
        logger.info(f"Distance to Entry: {distance:.2f}")
        logger.info(f"Spread: {spread}")
        return True
    else:
        if time.time() % 60 == 0:  # Log once per minute
            logger.info("\n=== Waiting for Entry ===")
            logger.info(f"Current Price: {current_price:.2f}")
            logger.info(f"Golden Ratio Target: {golden_level:.2f}")
            logger.info(f"Distance to Entry: {distance:.2f}")
            if distance <= margin * 2:
                logger.info("⚠️ Price approaching entry zone")
        return False


def run_fibonacci_strategy():
    """Main strategy execution loop with strict market condition requirements"""
    TRADE_COOLDOWN = 300
    CHECK_INTERVAL = 10
    MARKET_CHECK_INTERVAL = 3600

    last_trade_time = 0
    last_log_time = 0
    last_market_check = 0
    active_trade = False
    market_suitable = False

    logger.info("\n=== Starting Market Analysis ===")

    while True:
        try:
            current_time = time.time()

            # Regular market condition check
            if current_time - last_market_check > MARKET_CHECK_INTERVAL or not market_suitable:
                conditions, suitable = check_market_conditions()

                logger.info("\n=== Market Conditions Analysis ===")
                for timeframe, analysis in conditions.items():
                    logger.info(f"{timeframe} Timeframe:")
                    logger.info(f"  Trend: {analysis['trend']}")
                    logger.info(f"  Strength: {analysis['strength']}")
                    logger.info(f"  Price Change: {analysis['change_percent']}%")

                market_suitable = suitable
                if market_suitable:
                    logger.info("\n✅ Market conditions suitable for buy strategy!")
                    logger.info("Bot will now look for entries at the golden ratio level")
                else:
                    logger.warning("\n⚠️ Market conditions not suitable for trading")
                    logger.warning("Bot will analyze but not place trades")
                    time.sleep(300)  # Wait 5 minutes before rechecking
                    continue

                last_market_check = current_time

            # Only proceed with trading logic if market conditions are suitable
            if market_suitable:
                # Check for active positions
                positions = mt5.positions_get(symbol=config.SYMBOL)
                active_trade = positions and len(positions) > 0

                if active_trade:
                    if current_time - last_log_time >= 60:
                        logger.info("Active trade in progress - waiting for closure")
                        last_log_time = current_time
                    time.sleep(CHECK_INTERVAL)
                    continue

                if current_time - last_trade_time < TRADE_COOLDOWN:
                    if current_time - last_log_time >= 60:
                        remaining = int(TRADE_COOLDOWN - (current_time - last_trade_time))
                        logger.info(f"Cooldown: {remaining}s remaining")
                        last_log_time = current_time
                    time.sleep(CHECK_INTERVAL)
                    continue

                # Get and analyze price data
                data = get_price_data()
                if not data:
                    time.sleep(CHECK_INTERVAL)
                    continue

                high = max([d['high'] for d in data])
                low = min([d['low'] for d in data])
                fib_levels = calculate_fibonacci_levels(high, low)

                tick = mt5.symbol_info_tick(config.SYMBOL)
                if tick is None:
                    time.sleep(CHECK_INTERVAL)
                    continue

                current_price = tick.ask

                if check_entry_conditions(current_price, fib_levels):
                    logger.info("\n🎯 ENTRY SIGNAL DETECTED")
                    sl_price, tp_price = get_fib_based_stops(current_price, fib_levels)

                    # Log trade setup
                    logger.info("\n=== Trade Setup ===")
                    logger.info(f"Entry Price: {current_price:.2f}")
                    logger.info(f"Stop Loss: {sl_price:.2f}")
                    logger.info(f"Take Profit: {tp_price:.2f}")
                    logger.info(f"Risk/Reward: {abs(tp_price - current_price) / abs(current_price - sl_price):.2f}")

                    if trade.place_order(current_price, sl_price, tp_price, mt5.ORDER_TYPE_BUY):
                        logger.info("✅ Trade successfully placed")
                        last_trade_time = current_time
                    else:
                        logger.error("❌ Failed to place trade")

            time.sleep(CHECK_INTERVAL)

        except Exception as e:
            logger.error(f"Strategy error: {e}")
            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            logger.info("Strategy stopped by user")
            break


def check_market_conditions():
    """
    Checks market conditions across multiple timeframes
    Returns: (dict of conditions, boolean indicating if suitable for trading)
    """
    try:
        # Define timeframes to check
        timeframes = {
            mt5.TIMEFRAME_H4: "H4",
            mt5.TIMEFRAME_H1: "H1",
            mt5.TIMEFRAME_M15: "M15"
        }

        conditions = {}
        overall_suitable = True

        for tf, tf_name in timeframes.items():
            # Get the last 50 candles for analysis
            rates = mt5.copy_rates_from_pos(config.SYMBOL, tf, 0, 50)
            if rates is None:
                logger.error(f"Failed to get data for {tf_name}")
                return None, False

            df = pd.DataFrame(rates)

            # Calculate EMAs
            df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
            df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()

            # Get current values
            current_price = df['close'].iloc[-1]
            ema20 = df['ema20'].iloc[-1]
            ema50 = df['ema50'].iloc[-1]

            # Calculate trend strength
            price_change = ((current_price - df['close'].iloc[0]) / df['close'].iloc[0]) * 100

            # Check if price is making higher highs and higher lows
            last_5_highs = df['high'].rolling(window=5).max()
            last_5_lows = df['low'].rolling(window=5).min()
            higher_highs = last_5_highs.iloc[-1] > last_5_highs.iloc[-6]
            higher_lows = last_5_lows.iloc[-1] > last_5_lows.iloc[-6]

            # Determine trend
            if current_price > ema20 > ema50 and higher_highs and higher_lows:
                trend = "UPTREND"
                strength = "STRONG" if price_change > 0.5 else "MODERATE"
            elif current_price < ema20 < ema50:
                trend = "DOWNTREND"
                strength = "STRONG" if price_change < -0.5 else "MODERATE"
            else:
                trend = "SIDEWAYS"
                strength = "WEAK"

            conditions[tf_name] = {
                "trend": trend,
                "strength": strength,
                "change_percent": round(price_change, 2)
            }

            # Check if conditions are suitable for our buy strategy
            # We want uptrend on higher timeframes (H4 and H1)
            if tf in [mt5.TIMEFRAME_H4, mt5.TIMEFRAME_H1]:
                if trend != "UPTREND" or strength == "WEAK":
                    overall_suitable = False

        return conditions, overall_suitable

    except Exception as e:
        logger.error(f"Error in market conditions check: {e}")
        return None, False