from utils import *
from db_conn import query
import argparse
import time
import telegram_send

parser = argparse.ArgumentParser()
parser.add_argument("--coin", required=True)
args = parser.parse_args()

COIN = args.coin
COIN_PAIR = COIN + 'BUSD'

if __name__ == "__main__":

    while True:
        new_order = False
        prediction = model_prediction()
        signal_ind_buy = signal_indicator('BUY', prediction)
        coin_price = get_price()
        now = datetime.now()

        print(prediction[-1], signal_ind_buy)
        query('data', [now, prediction[-1], coin_price, signal_ind_buy, 0, COIN_PAIR])

        if (new_order is False) and (signal_ind_buy == 1):
            AMOUNT = 10
            # Transfer from Spot to Margin
            # client.margin_transfer(asset="BUSD", amount=AMOUNT, type=1)
            #
            # # Borrow the max amount
            # max_borrow_amount = float(client.margin_max_borrowable('BUSD')['amount']) * .9
            # borrow_response = client.margin_borrow(asset="BUSD", amount=max_borrow_amount)
            #
            # # place order
            # quantity = ((AMOUNT + max_borrow_amount) / coin_price) * .996
            # response = place_buy_order(quantity=quantity)
            #
            # # save information for later
            # price_bought = float(response['fills'][0]['price'])
            # timestamp = int(response['transactTime'])
            price_bought = coin_price
            timestamp = datetime.now()
            # Send a note
            telegram_send.send(messages=[f"{COIN} enter trade \nAmount: {AMOUNT}, Current Price: {coin_price}"])

            # enter the next while loop
            new_order = True

            while new_order is True:
                # predict, update stop loss and get current price
                prediction = model_prediction()
                current_price = get_price()
                signal_ind_sell = signal_indicator(type='SELL', prediction=prediction)
                now = datetime.now()
                # stop_loss = stoploss(timestamp=timestamp, price_bought=price_bought)

                # Save data
                query('data', [now, prediction[-1], current_price, signal_ind_sell, 1, COIN_PAIR])

                print('prediciton', prediction[-1])
                print('current_price', current_price)
                # print('stoploss', stop_loss)

                # sell if prediction OR sell signal is True
                # or (current_price < stop_loss)
                if (signal_ind_sell == 1):
                    # or (profit(price_bought=price_bought, current_price=current_price) is True):
                    # Place sell order and repay
                    # place_sell_order(quantity=get_margin_available_amount())
                    wining_percentage = percentage_calculator(price_bought, current_price)
                    # query('trade', [now, COIN, wining_percentage])

                    # try:
                    #     max_transferable_amount = float(client.margin_max_transferable('BUSD')['amount'])
                    #     client.margin_transfer(asset="BUSD", amount=max_transferable_amount, type=2)
                    #
                    # except:
                    #     print('error transfer')

                    # Send notification
                    telegram_send.send(messages=[f"Sold {COIN}! "
                                                 f"\nI made {wining_percentage}!"])
                    print('sold!', wining_percentage)

                    new_order = False
                    break

                # Else wait and repeat!
                else:
                    print('wait to sell')
                    time.sleep(60)

        print('wait to buy')
        time.sleep(60)
