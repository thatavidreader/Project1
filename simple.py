import logging
from kiteconnect import KiteConnect
import datetime
import sqlite3

logging.basicConfig(level=logging.DEBUG)  

# initialize Kite Connect client
kite = KiteConnect(api_key="tcic9nehief6209i")
kite.set_access_token("api_key")

#add stock tokens
stock_tokens = {
    "RELIANCE": 738561,
    "INFY": 408065,
}

# create/update database and tables
def create_or_update_database():
    conn = sqlite3.connect("stocks.db")
    cursor = conn.cursor()
    for stock in stock_tokens.keys():
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {stock} (
                date TEXT PRIMARY KEY,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                candle_pattern TEXT,
                candle_direction TEXT,
                trend TEXT,
                support_1 REAL,
                resistance_1 REAL,
                support_2 REAL,
                resistance_2 REAL
            )
        """)

        cursor.execute(f"PRAGMA table_info({stock})")
        columns = [col[1] for col in cursor.fetchall()]
        if 'candle_pattern' not in columns:
            cursor.execute(f"ALTER TABLE {stock} ADD COLUMN candle_pattern TEXT")
        if 'candle_direction' not in columns:
            cursor.execute(f"ALTER TABLE {stock} ADD COLUMN candle_direction TEXT")
        if 'trend' not in columns:
            cursor.execute(f"ALTER TABLE {stock} ADD COLUMN trend TEXT")
        if 'support_1' not in columns:
            cursor.execute(f"ALTER TABLE {stock} ADD COLUMN support_1 REAL")
        if 'resistance_1' not in columns:
            cursor.execute(f"ALTER TABLE {stock} ADD COLUMN resistance_1 REAL")
        if 'support_2' not in columns:
            cursor.execute(f"ALTER TABLE {stock} ADD COLUMN support_2 REAL")
        if 'resistance_2' not in columns:
            cursor.execute(f"ALTER TABLE {stock} ADD COLUMN resistance_2 REAL")
    conn.commit()
    conn.close()

# fetcj historical data
def fetch_historical_data(instrument_token, from_date, to_date, interval="day"):
    data = kite.historical_data(
        instrument_token=instrument_token,
        from_date=from_date,
        to_date=to_date,
        interval=interval
    )
    return data

# find the type of candlestick pattern
def determine_candle_pattern(record):
    body = abs(record["close"] - record["open"])
    upper_shadow = record["high"] - max(record["close"], record["open"])
    lower_shadow = min(record["close"], record["open"]) - record["low"]
    
    if body == 0:
        return "Doji"
    elif body / (record["high"] - record["low"]) > 0.8:
        return "Marubozu"
    elif lower_shadow > 2 * body and record["close"] > record["open"]:
        return "Hammer"
    elif lower_shadow > 2 * body and record["close"] < record["open"]:
        return "Hanging Man"
    elif upper_shadow > 2 * body and record["close"] < record["open"]:
        return "Shooting Star"
    elif upper_shadow > 2 * body and record["close"] > record["open"]:
        return "Inverted Hammer"
    else:
        return "Normal"

# determineBullish or Bearish
def determine_candle_direction(record):
    if record["close"] > record["open"]:
        return "Bullish"
    elif record["close"] < record["open"]:
        return "Bearish"
    else:
        return "Neutral"

# calculate support and resistance using pivot points
def calculate_support_resistance(record):
    pivot_point = (record["high"] + record["low"] + record["close"]) / 3
    support_1 = (2 * pivot_point) - record["high"]
    resistance_1 = (2 * pivot_point) - record["low"]
    support_2 = pivot_point - (record["high"] - record["low"])
    resistance_2 = pivot_point + (record["high"] - record["low"])
    return support_1, resistance_1, support_2, resistance_2

#support of last five days, 
# support_1 = 

# store data in SQLite database
def store_data_in_database(stock, data, trends):
    conn = sqlite3.connect("stocks.db")
    cursor = conn.cursor()
    for record in data:
        candle_pattern = determine_candle_pattern(record)
        candle_direction = determine_candle_direction(record)
        trend = trends.get(record["date"], "Sideway")
        support_1, resistance_1, support_2, resistance_2 = calculate_support_resistance(record)
        cursor.execute(f"""
            INSERT OR REPLACE INTO {stock} (date, open, high, low, close, volume, candle_pattern, candle_direction, trend, support_1, resistance_1, support_2, resistance_2)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (record["date"], record["open"], record["high"], record["low"], record["close"], record["volume"],
              candle_pattern, candle_direction, trend, support_1, resistance_1, support_2, resistance_2))
    conn.commit()
    conn.close()

# get data from SQLite database
def fetch_data_from_db(stock):
    conn = sqlite3.connect("stocks.db")
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {stock} ORDER BY date DESC")
    rows = cursor.fetchall()
    conn.close()
    return rows

# calculate trend based on the last 5 days
def calculate_trend(data):
    trends = {}
    sorted_data = sorted(data, key=lambda x: x[0])
    for i in range(5, len(sorted_data)):
        period_data = sorted_data[i-5:i]
        closes = [d[4] for d in period_data]
        if closes[-1] > closes[0]:
            trend = "Uptrend"
        elif closes[-1] < closes[0]:
            trend = "Downtrend"
        else:
            trend = "Sideway"
        trends[sorted_data[i][0]] = trend
    return trends

# determine buy value and stop loss
def determine_buy_and_stop_loss(data):
    latest_record = data[-1]
    trend = latest_record[8]
    support_1 = latest_record[9]
    resistance_1 = latest_record[10]

    if trend == "Uptrend":
        buy_value = latest_record.close  # Buy at the latest closing price
        stop_loss = support_1 * 0.98  # Set stop loss 2% below the nearest support level
        logging.info(f"Buy value: {buy_value}, Stop loss: {stop_loss}")
        return buy_value, stop_loss, "buy"
    elif trend == "Downtrend":
        sell_value = latest_record.close  # Short sell at the latest closing price
        stop_loss = resistance_1 * 1.02  # Set stop loss 2% above the nearest resistance level
        logging.info(f"Sell value: {sell_value}, Stop loss: {stop_loss}")
        return sell_value, stop_loss, "sell"
    else:
        logging.info("No trade signal as the trend is sideways.")
        return None, None, None

def main():
    # create/update the database and tables
    create_or_update_database()

    # define range
    to_date = datetime.datetime.now()
    from_date = to_date - datetime.timedelta(days=365)

    # get historical data
    historical_data = {}
    for stock, token in stock_tokens.items():
        historical_data[stock] = fetch_historical_data(token, from_date, to_date)
        #calculate trend immediately after fetching the data
        db_data = [(record["date"], record["open"], record["high"], record["low"], record["close"], record["volume"]) for record in historical_data[stock]]
        trends = calculate_trend(db_data)
        store_data_in_database(stock, historical_data[stock], trends)

        # get data from the database to calculate buy value and stop loss
        db_data = fetch_data_from_db(stock)
        trade_value, stop_loss, action = determine_buy_and_stop_loss(db_data)
        if trade_value and stop_loss:
            print(f"Stock: {stock}, Action: {action.capitalize()}, Value: {trade_value}, Stop Loss: {stop_loss}")


if __name__ == "__main__":
    main()

