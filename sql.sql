###########################
##### Procedure List #####
###########################

CREATE PROCEDURE data(
    IN s_timestamp datetime,
    IN s_prediction float,
    IN s_price float,
    IN s_signal float,
    IN s_type int,
    IN s_coin text
    )
BEGIN
    INSERT INTO data (timestamp, prediction, price, singal, type, coin)
    VALUES (s_timestamp, s_prediction, s_price, s_signal, s_type, s_coin);
END;

############################

CREATE PROCEDURE trade(
    IN s_timestamp datetime,
    IN s_type int,
    IN s_price float,
    IN s_amount float,
    IN s_total_earn float,
    IN s_coin text
    )
BEGIN
    INSERT INTO trades (timestamp, type, price, amount, total_earn, coin)
    VALUES (s_timestamp, s_type, s_price, s_amount, s_total_earn, s_coin);
END;

############################

CREATE PROCEDURE price_prediction_fig()
BEGIN
    SELECT timestamp, prediction, price
    FROM data
    ORDER BY timestamp;
END;

############################

CREATE PROCEDURE update_status(
    IN s_coin text,
    IN s_prediction float,
    IN s_signals int,
    IN s_date datetime,
    IN s_on_trade int
)
BEGIN
    UPDATE status
    SET prediction = s_prediction,
        signals = s_signals,
        last_update = s_date,
        on_trade = s_on_trade
    WHERE coin = s_coin;
END;