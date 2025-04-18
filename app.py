from flask import Flask, render_template, request
import requests
import pygal
import os
import csv
from datetime import datetime

app = Flask(__name__)

# API Credentials
API_KEY = "L0WWWUGT9503R130"
BASE_URL = "https://www.alphavantage.co/query"

# Load stock data from CSV
def load_stocks():
    stocks = []
    with open('stocks.csv', 'r') as file:
        csv_reader = csv.reader(file)
        next(csv_reader)
        for row in csv_reader:
            stocks.append({
                'symbol': row[0],
                'name': row[1],
                'sector': row[2]
            })
    return stocks

# Fetch data from Alpha Vantage API
def fetch_data(symbol, time_series_function, start_date, end_date, time_series_option):
    params = {
        "function": time_series_function,
        "symbol": symbol,
        "apikey": API_KEY,
        "outputsize": "full"
    }

    if time_series_option == 1:
        params["interval"] = "60min"
        params["month"] = "{}-{:02}".format(start_date.year, start_date.month)
    
    try:
        response = requests.get(BASE_URL, params=params)
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

# Parse stock data
def get_stock_data(data, time_series_option, start_date, end_date):
    keys = list(data.keys())
    if len(keys) < 2:
        return None, [], [], [], []
    
    time_series_data = keys[1]
    
    open_prices = []
    high_prices = []
    low_prices = []
    close_prices = []
    
    time_series = data.get(time_series_data)
    if not time_series:
        return None, [], [], [], []

    filtered_time_series = {}
    
    if time_series_option == 1:
        filtered_time_series = {
            timestamp: values for timestamp, values in time_series.items()
            if start_date <= datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S") <= end_date
        }

    else:
        filtered_time_series = {
            timestamp: values for timestamp, values in time_series.items()
            if start_date <= datetime.strptime(timestamp, "%Y-%m-%d") <= end_date
        }
    
    sorted_timestamps = sorted(filtered_time_series.keys())
    sorted_filtered_time_series = {timestamp: filtered_time_series[timestamp] for timestamp in sorted_timestamps}
    
    for timestamp, values in sorted_filtered_time_series.items():
        open_price = values.get('1. open')
        open_prices.append(float(open_price))
        high_price = values.get('2. high')
        high_prices.append(float(high_price))
        low_price = values.get('3. low')
        low_prices.append(float(low_price))
        close_price = values.get('4. close')
        close_prices.append(float(close_price))

    return sorted_filtered_time_series, open_prices, high_prices, low_prices, close_prices

# Generate chart using pygal
def generate_chart(chart_type, symbol, time_series_option, start_date, end_date, dates, open_prices, high_prices, low_prices, close_prices):
    if chart_type == 1:
        chart = pygal.Bar()
    else:
        chart = pygal.Line()
    
    chart.title = f'Stock Data for {symbol}: {start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")}'
    chart.x_labels = dates
    chart.x_label_rotation = 45
    
    chart.add('Open', open_prices)
    chart.add('High', high_prices)
    chart.add('Low', low_prices)
    chart.add('Close', close_prices)
    
    chart_filename = f'chart_{datetime.now().strftime("%Y%m%d%H%M%S")}.svg'
    chart_path = os.path.join('static', chart_filename)
    chart.render_to_file(chart_path)
    
    return chart_filename

@app.route('/', methods=['GET', 'POST'])
def index():
    stocks = load_stocks()
    chart_filename = None
    error_message = None
    
    if request.method == 'POST':
        try:
            symbol = request.form.get('symbol')
            chart_type = int(request.form.get('chart_type'))
            time_series_option = int(request.form.get('time_series'))
            
            start_date_str = request.form.get('start_date')
            end_date_str = request.form.get('end_date')
            
            start_date_str = start_date_str.replace(" ", "")
            end_date_str = end_date_str.replace(" ", "")
            
            try:
                if '/' in start_date_str:
                    start_date = datetime.strptime(start_date_str, "%m/%d/%Y")
                else:
                    start_date = datetime.strptime(start_date_str, "%m-%d-%Y")
                    
                if '/' in end_date_str:
                    end_date = datetime.strptime(end_date_str, "%m/%d/%Y")
                else:
                    end_date = datetime.strptime(end_date_str, "%m-%d-%Y")
            except ValueError:
                try:
                    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
                    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
                except ValueError:
                    raise ValueError("Date format not recognized. Please use mm/dd/yyyy format.")
            
            time_series_map = {
                1: "TIME_SERIES_INTRADAY",
                2: "TIME_SERIES_DAILY",
                3: "TIME_SERIES_WEEKLY",
                4: "TIME_SERIES_MONTHLY"
            }
            time_series_function = time_series_map.get(time_series_option)
            
            data = fetch_data(symbol, time_series_function, start_date, end_date, time_series_option)
            
            if data and "Error Message" not in data:
                time_series, open_prices, high_prices, low_prices, close_prices = get_stock_data(
                    data, time_series_option, start_date, end_date
                )
                if time_series:
                    chart_filename = generate_chart(
                        chart_type, symbol, time_series_option, start_date, end_date,
                        list(time_series.keys()), open_prices, high_prices, low_prices, close_prices
                    )
                else:
                    error_message = "No data available for the selected date range."
            else:
                error_message = "Failed to fetch data from API. Please try again."
        except ValueError as ve:
            error_message = str(ve)
        except Exception as e:
            error_message = f"An error occurred: {str(e)}"
    
    return render_template('index.html', stocks=stocks, chart_filename=chart_filename, error_message=error_message)

if __name__ == '__main__':
    os.makedirs('static', exist_ok=True)
    app.run(host="0.0.0.0")