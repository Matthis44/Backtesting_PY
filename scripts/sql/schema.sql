-- Securities master: reference data (vendors, symbols) and daily prices.
-- Usage: mysql -u <user> -p < scripts/sql/schema.sql

CREATE DATABASE IF NOT EXISTS securities_master;
USE securities_master;

CREATE TABLE IF NOT EXISTS data_vendor (
    id                INT          NOT NULL AUTO_INCREMENT,
    name              VARCHAR(64)  NOT NULL,
    website_url       VARCHAR(255) NULL,
    created_date      DATETIME     NOT NULL,
    last_updated_date DATETIME     NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_vendor_name (name)
);

CREATE TABLE IF NOT EXISTS symbol (
    id                INT          NOT NULL AUTO_INCREMENT,
    ticker            VARCHAR(32)  NOT NULL,
    instrument        VARCHAR(64)  NOT NULL,
    name              VARCHAR(255) NULL,
    sector            VARCHAR(255) NULL,
    currency          VARCHAR(32)  NULL,
    created_date      DATETIME     NOT NULL,
    last_updated_date DATETIME     NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_symbol_ticker (ticker)
);

CREATE TABLE IF NOT EXISTS daily_price (
    id                BIGINT         NOT NULL AUTO_INCREMENT,
    data_vendor_id    INT            NOT NULL,
    symbol_id         INT            NOT NULL,
    price_date        DATE           NOT NULL,
    created_date      DATETIME       NOT NULL,
    last_updated_date DATETIME       NOT NULL,
    open_price        DECIMAL(19, 4) NULL,
    high_price        DECIMAL(19, 4) NULL,
    low_price         DECIMAL(19, 4) NULL,
    close_price       DECIMAL(19, 4) NULL,
    adj_close_price   DECIMAL(19, 4) NULL,
    volume            BIGINT         NULL,
    PRIMARY KEY (id),
    -- one price per symbol, vendor and day: makes reloads idempotent
    UNIQUE KEY uq_price (data_vendor_id, symbol_id, price_date),
    KEY idx_symbol_date (symbol_id, price_date),
    CONSTRAINT fk_price_vendor FOREIGN KEY (data_vendor_id) REFERENCES data_vendor (id),
    CONSTRAINT fk_price_symbol FOREIGN KEY (symbol_id) REFERENCES symbol (id)
);

INSERT IGNORE INTO data_vendor (name, website_url, created_date, last_updated_date)
VALUES ('Yahoo Finance', 'https://finance.yahoo.com', NOW(), NOW());
