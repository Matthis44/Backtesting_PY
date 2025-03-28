#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import mysql.connector

DB_CONFIG = {
    "host": "localhost",
    "user": "sec_user",
    "password": "1Lo2Ma3Is@",
    "database": "securities_master"
}

if __name__ == "__main__":
    con = mysql.connector.connect(**DB_CONFIG)

    sql = """
    SELECT dp.price_date, dp.adj_close_price
    FROM symbol AS sym
    INNER JOIN daily_price AS dp ON dp.symbol_id = sym.id
    WHERE sym.ticker = 'GOOG'
    ORDER BY dp.price_date ASC;
    """

    df = pd.read_sql(sql, con, index_col="price_date", parse_dates=["price_date"])
    print(df.tail())
