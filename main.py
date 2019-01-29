import requests, string, json, time, apiKey, mysql.connector, re
from twilio.rest import Client
from mysql.connector import errorcode

api = apiKey.apiKey
client = Client(apiKey.twilio_sid, apiKey.twilio_auth_token)
app_number = apiKey.twilio_number

getRe = re.compile('(get)\s(alarms|price)\s*(\w+(\.\w+)*)*')
setRe = re.compile('(set)\s(alarm)\s(\w+(\.\w+)*)\s(above|below)\s(\d+[.|,]*\d*)')

j = 0
while(1):
    try:
        conn = mysql.connector.connect(**apiKey.sqlConnect)
        print(conn)
    except mysql.connector.Error as e:
        if (e.errno == errorcode.ER_ACCESS_DENIED_ERROR):
            print("Wrong username/password combination")
        elif (e.errno == errorcode.ER_BAD_DB_ERROR):
            print("Database doesn't exist")
        else:
            print(e)
        continue

    cursor = conn.cursor(buffered=True)

    query = ("SELECT iden, number, body FROM requests WHERE processed = 0")

    cursor.execute(query)
    try:
        response = ""
        for (iden, number, body) in cursor:
            print("Checking for requests!")
            response = ""
            rIden = iden
            rNumber = number
            rBody = body.lower()

            print("Received request from {} with body {}.".format(rNumber, rBody))

            if(rBody == "h"):
                response = "get alarms: Shows you all of your active alarms\n" \
                           "get alarms [stock]: Shows you all of your active alarms for [stock]\n" \
                           "get price [stock]: Shows you the current price of [stock]\n" \
                           "set alarm [stock] [above|below] [price]: sets an alarm for when [stock] price " \
                           "goes [above or below] [price]\n" \
                           "h: Shows the help menu"
            if(getRe.match(rBody)):
                print("Match for get regexp!")
                rBody = rBody.split(" ")
                if(rBody[1] == "alarms"):
                    if(len(rBody) >= 3):
                        print("Getting alarms for {}".format(rBody[2]))
                        response += "You have the current alarms set for {}:\n".format(rBody[2].upper())

                        cursor2 = conn.cursor(buffered=True)

                        query = ("SELECT number, stock, value, moves, rang "
                                 "FROM alarms WHERE number = '" + rNumber + "' AND stock = '" + rBody[2] + "' AND rang = 0")

                        cursor2.execute(query)
                        if(cursor2.rowcount == 0):
                            response = "You have no alarms set for this stock."
                        else:
                            for (number, stock, value, moves, rang) in cursor2:
                                response += "Price moves {} {}$\n".format(moves, value)

                        cursor2.close()
                    else:
                        response = "You have the current alarms set:\n"

                        cursor2 = conn.cursor(buffered=True)

                        query = ("SELECT number, stock, value, moves, rang "
                                 "FROM alarms WHERE number = '" + rNumber + "' AND rang = 0")

                        cursor2.execute(query)
                        if (cursor2.rowcount == 0):
                            response = "You have no alarms set."
                        else:
                            for (number, stock, value, moves, rang) in cursor2:
                                response += "{} price moves {} {}$\n".format(stock.upper(), moves, value)

                        cursor2.close()

                elif(rBody[1] == "price"):
                    print("I see it's a price request...")
                    if(len(rBody) > 2):
                        print("Getting price for {}".format(rBody[2]))

                        while(1):
                            error = ""
                            try:
                                r = requests.get(
                                    "https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=" + rBody[2] + "&interval=1min&apikey=" + api)
                                stockPrice = r.json()
                                for i in stockPrice:
                                    if (i == "Error Message"):
                                        print("wrong stock!")
                                        response = "The stock {} doesn't exist.  If you are looking for a toronto stock, don't forget" \
                                                   " to place the suffix '.to' at the end of your stock name.  ex: gxe.to".format(rBody[2])
                                        error ="Wrong stock"
                                        break
                                    elif(i == "Information"):
                                        print("too many API calls")
                                        error = "Too many API calls"
                                        break

                                if(error != ""):
                                    print("error")
                                    raise ValueError(error)

                                if (r.status_code != 200):
                                    raise ValueError("API broke lol")

                                else:
                                    stockPrice = stockPrice["Time Series (1min)"]
                                    for i in stockPrice:
                                        stockPrice = float(stockPrice[i]["4. close"])
                                        break
                                    response = "{} current price is {}$".format(rBody[2].upper(), stockPrice)
                                    print("Price is {}".format(stockPrice))
                                    break
                            except ValueError as e:
                                print(e)
                                if (e == ValueError("Wrong stock")):
                                    print("breaking")
                                    break
                                else:
                                    time.sleep(30)
                                continue
                    else:
                        response = "Cannot fetch price of an empty stock!  The correct command structure is:\n" \
                        "get price [stock]"

            elif(setRe.match(rBody)):
                print("Set alarm match!")
                rBody = rBody.split(" ")

                while(1):
                    error = ""
                    try:
                        r = requests.get(
                            "https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=" + rBody[
                                2] + "&interval=1min&apikey=" + api)

                        stockPrice = r.json()
                        for i in stockPrice:
                            if (i == "Error Message"):
                                response = "The stock {} doesn't exist.  If you are looking for a toronto stock, don't forget" \
                                           " to place the suffix '.to' at the end of your stock name.  ex: gxe.to".format(
                                    rBody[2])
                                error = "Wrong stock"
                                break
                            elif (i == "Information"):
                                print("too many API calls")
                                error = "Too many API calls"
                                break

                        if (error != ""):
                            raise ValueError(error)

                        if (r.status_code != 200):
                            raise ValueError("API broke lol")
                        else:
                            cursor2 = conn.cursor(buffered=True)

                            query = "INSERT into alarms(number, stock, value,  moves, rang) VALUES(%s, %s, %s, %s, %s)"

                            cursor2.execute(query, (rNumber, rBody[2], rBody[4], rBody[3], 0))
                            conn.commit()

                            cursor2.close()

                            response = "Alarm set for {} moves {} {}$".format(rBody[2].upper(), rBody[3], rBody[4])
                            print("Alarm set for {} moves {} {}$".format(rBody[2].upper(), rBody[3], rBody[4]))
                            break

                    except ValueError as e:
                        if (error == "Wrong stock"):
                            break
                        else:
                            time.sleep(30)
                            continue

            query = ("UPDATE requests SET processed=%s WHERE iden=%s")
            cursor.execute(query, (1, rIden))

            conn.commit()
            print("Updated processed to 1 for this request.")
            if (response != ""):
                message = client.messages.create(
                    to=rNumber,
                    from_=app_number,
                    body=response)
                print("Message sent to {} with id {}".format(rNumber, message.sid))

    except:
        continue

    cursor.close()

    cursor = conn.cursor(buffered=True)

    query = ("SELECT iden, number, stock, value, moves FROM alarms WHERE rang = 0")

    cursor.execute(query)

    stocks = {}

    row = cursor.fetchall()
    for t in row:
        print("fetching a stock")
        rNumber = t[1]
        rIden = t[0]
        stock = t[2]
        moves = t[4]
        value = t[3]
        response = ""
        retries = 0

        while(retries < 3):
            if (stock in stocks.keys()):
                break
            else:
                try:
                    r = requests.get(
                        "https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=" + stock + "&interval=1min&apikey=" + api)

                    sp = r.json()
                    for i in sp:
                        if (i == "Information"):
                            raise ValueError("Too many API calls")
                        else:
                            break

                    if(r.status_code != 200):
                        raise ValueError("API broke lol")
                    try:
                        stockPrice = sp["Time Series (1min)"]
                    except:
                        retries += 1
                        print(retries)
                        continue
                    break
                except:
                    time.sleep(30)
                    continue

        if(retries == 3):
            continue
        if(stock not in stocks.keys()):
            for s in stockPrice:
                price = float(stockPrice[s]["4. close"])
                break

            stocks[stock] = price
        rn = 0

        print(stocks)
        print("Checking for {}".format(stock))
        if(moves == "above"):
            if(stocks[stock] > value):
                response = "PRICE ALERT!\n {} price is now above {}$.  Its price is {}$.".format(stock.upper(), value, stocks[stock])
                rn = 1
        else:
            if(stocks[stock] < value):
                response = "PRICE ALERT!\n {} price is now below {}$.  Its price is {}$.".format(stock.upper(), value, stocks[stock])
                rn = 1

        while(1):
            try:
                query = ("UPDATE alarms SET rang=%s WHERE iden=%s")
                cursor.execute(query, (rn, rIden))
                conn.commit()
            except:
                continue
            else:
                break

        if (response != ""):
                message = client.messages.create(
                    to=rNumber,
                    from_=app_number,
                    body=response)


    cursor.close()
    conn.close()

    time.sleep(10)
