CREATE TYPE user_role AS ENUM ('USER', 'ADMIN');

CREATE TYPE order_status AS ENUM ('NEW', 'EXECUTED', 'PARTIALLY_EXECUTED', 'CANCELLED');

CREATE TYPE order_direction AS ENUM ('BUY', 'SELL');

-- Create Users Table
CREATE TABLE users (
                       id UUID PRIMARY KEY,
                       name VARCHAR(255) NOT NULL CHECK (LENGTH(name) >= 3),
                       role VARCHAR(50) NOT NULL DEFAULT 'USER' CHECK (role IN ('USER', 'ADMIN')),
                       api_key VARCHAR(255) NOT NULL
);

-- Create Instruments Table
CREATE TABLE instruments (
                             name VARCHAR(255) NOT NULL,
                             ticker VARCHAR(10) NOT NULL CHECK (ticker ~ '^[A-Z]{2,10}$') PRIMARY KEY
    );

-- Create Transactions Table
CREATE TABLE transactions (
                              id UUID PRIMARY KEY,
                              ticker VARCHAR(10) NOT NULL REFERENCES instruments(ticker),
                              amount INT NOT NULL,
                              price INT NOT NULL,
                              timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create Deposit Requests Table
CREATE TABLE deposit_requests (
                                  id UUID PRIMARY KEY,
                                  ticker VARCHAR(10) NOT NULL REFERENCES instruments(ticker),
                                  amount INT NOT NULL CHECK (amount > 0)
);

-- Create Withdraw Requests Table
CREATE TABLE withdraw_requests (
                                   id UUID PRIMARY KEY,
                                   ticker VARCHAR(10) NOT NULL REFERENCES instruments(ticker),
                                   amount INT NOT NULL CHECK (amount > 0)
);

-- Create Limit Orders Table
CREATE TABLE limit_orders (
                              id UUID PRIMARY KEY,
                              status VARCHAR(50) NOT NULL CHECK (status IN ('NEW', 'EXECUTED', 'PARTIALLY_EXECUTED', 'CANCELLED')),
                              user_id UUID NOT NULL REFERENCES users(id),
                              timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                              price INT NOT NULL CHECK (price > 0),
                              direction VARCHAR(50) NOT NULL CHECK (direction IN ('BUY', 'SELL')),
                              ticker VARCHAR(10) NOT NULL REFERENCES instruments(ticker),
                              qty INT NOT NULL CHECK (qty >= 1),
                              filled INT NOT NULL DEFAULT 0
);

-- Create Market Orders Table
CREATE TABLE market_orders (
                               id UUID PRIMARY KEY,
                               status VARCHAR(50) NOT NULL CHECK (status IN ('NEW', 'EXECUTED', 'PARTIALLY_EXECUTED', 'CANCELLED')),
                               user_id UUID NOT NULL REFERENCES users(id),
                               timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                               direction VARCHAR(50) NOT NULL CHECK (direction IN ('BUY', 'SELL')),
                               ticker VARCHAR(10) NOT NULL REFERENCES instruments(ticker),
                               qty INT NOT NULL CHECK (qty >= 1)
);

-- Create Order Responses Table
CREATE TABLE order_responses (
                                 id UUID PRIMARY KEY,
                                 success BOOLEAN NOT NULL DEFAULT TRUE,
                                 order_id UUID NOT NULL
);

CREATE TABLE balances (
                          user_id UUID NOT NULL,
                          ticker VARCHAR(10) NOT NULL,
                          amount INTEGER NOT NULL DEFAULT 0,
                          PRIMARY KEY (user_id, ticker),
                          FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE orderbook (
                           id SERIAL PRIMARY KEY,
                           ticker VARCHAR(10) NOT NULL,
                           bid_levels JSON NOT NULL,
                           ask_levels JSON NOT NULL,
                           CONSTRAINT fk_orderbook_instruments
                               FOREIGN KEY (ticker)
                                   REFERENCES instruments (ticker)
                                   ON DELETE CASCADE,
                           CONSTRAINT uq_orderbook_ticker UNIQUE (ticker)
);