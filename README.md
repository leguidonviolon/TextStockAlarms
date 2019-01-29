# TextStockAlarms
A script to allow someone to setup alarms on stock prices using text messages on a cellphone.

This script works with Twilio, the text messaging api and alphavantage free stock price api.

Just enter your database's and twilio connection's infos in apiKey.py and start up the script.

The bot works with regexps to receive instructions.  The possible text message instructions are:
  get alarms: Shows you all of your active alarms
  get alarms [stock]: Shows you all of your active alarms for [stock]
  get price [stock]: Shows you the current price of [stock]
  set alarm [stock] [above|below] [price]: sets an alarm for when [stock] price goes [above or below] [price]
  h: Shows the help menu
  
To make sure we don't go over alphavantage's api rate limit, the bot fetches the instructions once every 10 seconds.
However, Alphavantage's api isn't very reliable so sometimes it's longer because it can't fetch the current price of
some stocks.

When an alarm is triggered by a price reaching it, the bot sends a text message to the person who set it up.
