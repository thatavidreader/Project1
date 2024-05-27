# 1. initialise kiteconnect api
# 2. add stock tokens
# 3. create database
# 4. get historical data
# 5. store in database
# 6. retrieve from database
# 7. calculate candle type (bearish bullish) candle trends and (support resistance)

import logging
from kiteconnect import KiteConnect
import datetime
import sqlite3

logging.basicConfig(level=logging.DEBUG) #login

kite = KiteConnect(api_key="tcic9nehief6209i") #replace with api key
kite.set_access_token("your_access_token") #replace with access token


stock_tokens = {
    "RELIANCE": 738561, #add stock token

}

#create sqlite database
def create_database():
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
                volume INTEGER
            )
        """)
    conn.commit()
    conn.close()

# get historical data
def fetch_historical_data(instrument_token, from_date, to_date, interval="day"):
    data = kite.historical_data(
        instrument_token=instrument_token,
        from_date=from_date,
        to_date=to_date,
        interval=interval
    )
    return data

# store data in database
def store_data_in_database(stock, data):
    conn = sqlite3.connect("stocks.db")
    cursor = conn.cursor()
    for record in data:
        cursor.execute(f"""
            INSERT OR REPLACE INTO {stock} (date, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (record["date"], record["open"], record["high"],
              record["low"], record["close"], record["volume"]))
    conn.commit()
    conn.close()

# get data from database
def fetch_data_from_db(stock):
    conn = sqlite3.connect("stocks.db")
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {stock} ORDER BY date DESC")
    rows = cursor.fetchall()
    conn.close()
    return rows

# calculate support and resistance
def calculate_support_resistance(data):
    sorted_data = sorted(data, key=lambda x: x[0], reverse=True)
    periods = [3, 5, 10, 15, 20, 120, 240]
    support_resistance = {}

    for period in periods:
        period_data = sorted_data[:period]
        lows = [d[4] for d in period_data]
        highs = [d[3] for d in period_data]
        support_resistance[period] = {
            'support': sorted(lows)[:3],
            'resistance': sorted(highs, reverse=True)[:3]
        }

    return support_resistance

# Identify candle type
def identify_candle_type(data):
    candles = []
    for record in data[-30:]:
        open_price = record[1]
        close_price = record[4]

        if close_price > open_price:
            candle_type = "Bullish"
        elif close_price < open_price:
            candle_type = "Bearish"
        else:
            candle_type = "Doji"

        candles.append({
            'date': record[0],
            'type': candle_type
        })
    return candles

# identify candle trends
def identify_trends(data):
    trends = []
    for i in range(-30, 0):
        if i-5 >= -len(data):
            trend_data = data[i-5:i]
            closes = [d[4] for d in trend_data]
            if closes[-1] > closes[0] and closes[-1] > closes[-2]:
                trend = "Uptrend"
            elif closes[-1] < closes[0] and closes[-1] < closes[-2]:
                trend = "Downtrend"
            elif closes[-1] > closes[-2] and closes[-2] < closes[-3]:
                trend = "Uptrend Reversal"
            elif closes[-1] < closes[-2] and closes[-2] > closes[-3]:
                trend = "Downtrend Reversal"
            else:
                trend = "Sideway Movement"
            trends.append({
                'date': data[i][0],
                'trend': trend
            })
    return trends


def main():
    
    create_database()

    #define date range
    to_date = datetime.datetime.now()
    from_date = to_date - datetime.timedelta(days=365)

    # get historical data
    historical_data = {}
    for stock, token in stock_tokens.items():
        historical_data[stock] = fetch_historical_data(token, from_date, to_date)
        store_data_in_database(stock, historical_data[stock])

    # Process data
    for stock, data in historical_data.items():
        db_data = fetch_data_from_db(stock)
        support_resistance = calculate_support_resistance(db_data)
        print(f"{stock} Support and Resistance: {support_resistance}")

        candle_types = identify_candle_type(db_data)
        print(f"{stock} Candle Types: {candle_types}")

        trends = identify_trends(db_data)
        print(f"{stock} Trends: {trends}")

if __name__ == "__main__":
    main()
