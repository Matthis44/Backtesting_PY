#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime
import requests
import warnings
import mysql.connector
import yfinance as yf

# --- Config ---
DB_CONFIG = {
    "host": "localhost",
    "user": "sec_user",
    "password": "1Lo2Ma3Is@",  # à adapter !
    "database": "securities_master"
}

# --- Connexion MySQL ---
con = mysql.connector.connect(**DB_CONFIG)

def obtain_list_of_db_tickers():
    with con.cursor() as cur:
        cur.execute("SELECT id, ticker FROM symbol")
        data = cur.fetchall()
        return [(d[0], d[1]) for d in data]


def get_daily_historic_data_yahoo(ticker, start_date="2000-01-01", end_date=None):
    try:
        df = yf.download(ticker,
                        start=start_date, 
                        end=end_date, 
                        progress=False,
                        auto_adjust=False)

        # Vérifie si la colonne 'Adj Close' existe
        if df.empty or 'Adj Close' not in df.columns:
            raise ValueError("Colonne 'Adj Close' manquante")

        df = df.dropna()
        prices = []
        for date, row in df.iterrows():
            prices.append((
                date.to_pydatetime(),  # price_date
                float(row['Open']),
                float(row['High']),
                float(row['Low']),
                float(row['Close']),
                int(row['Volume']),
                float(row['Adj Close'])
            ))
        return prices

    except Exception as e:
        print(f"Erreur yfinance pour {ticker} : {e}")
        return []
    
    
def format_ticker_yahoo(ticker):
    return ticker.replace('.', '-')



def insert_daily_data_into_db(data_vendor_id, symbol_id, daily_data):
    print(f"Insertion dans la base : {len(daily_data)} lignes pour symbol_id={symbol_id}")
    now = datetime.datetime.utcnow()
    data_to_insert = [
        (data_vendor_id, symbol_id, d[0], now, now, d[1], d[2], d[3], d[4], d[5], d[6])
        for d in daily_data
    ]
    column_str = """data_vendor_id, symbol_id, price_date, created_date,
    last_updated_date, open_price, high_price, low_price,
    close_price, volume, adj_close_price"""
    insert_str = ("%s, " * 11)[:-2]
    final_str = f"INSERT INTO daily_price ({column_str}) VALUES ({insert_str})"

    with con.cursor() as cur:
        cur.executemany(final_str, data_to_insert)
        con.commit()

if __name__ == "__main__":
    warnings.filterwarnings('ignore')

    tickers = obtain_list_of_db_tickers()
    for i, (symbol_id, ticker) in enumerate(tickers):
        yahoo_ticker = format_ticker_yahoo(ticker)
        print(f"({i+1}/{len(tickers)}) Téléchargement de {ticker} → {yahoo_ticker}")
        data = get_daily_historic_data_yahoo(yahoo_ticker)
        if data:
            insert_daily_data_into_db(1, symbol_id, data)
            print(f"{ticker} inséré avec succès.")
        