
from flask import Flask, render_template,request, jsonify,redirect 
import json
from pymongo import MongoClient
from statistics import mean, pstdev
import numpy as np
from datetime import datetime, timedelta
from math import floor


with open('config.json') as config_file:
    config = json.load(config_file)

start_date = datetime.strptime(config['start_date'], '%Y-%m-%d')

# Connect to MongoDB
uri = config['uri']
client = MongoClient(uri)
db = client[config['database']]
incubator = db[config['collection']]


app = Flask(__name__, static_folder='static',template_folder='templates')

def lock_down_and_hatch(start_date):
    lock_down_date = start_date + timedelta(days=18)
    hatch_date = start_date + timedelta(days=21)
    return lock_down_date,hatch_date

@app.route('/')
def index():
    lock_down_date, hatch_date = lock_down_and_hatch(start_date)
    cursor = incubator.find().sort("Timestamp", -1)
    historical_data = []
    for data in cursor:
        historical_data.append({
            'Time': data['Timestamp'],
            'Temperature(F)': data['Temperature(F)'],
            'Temperature Relay Status': data['Temperature Relay Status'],
            'Humidity(%)': data['Humidity(%)'],
            'Humidity Relay Status': data['Humidity Relay Status'],
            'Last Egg Turn': data['Last Egg Turn'],
            'Day in Egg Cycle': data['Day in Egg Cycle']
        })
        # Get last record and store it as current data
        if len(historical_data) == 1:
            current_data = {
                'temperature': data['Temperature(F)'],
                'temperature_relay_status': data['Temperature Relay Status'],
                'humidity': data['Humidity(%)'],
                'humidity_relay_status': data['Humidity Relay Status'],
                'last_relay_on': data['Last Egg Turn'],
                'day_in_cycle': data['Day in Egg Cycle'],
            }

    # New function to get statistical information
    egg_cycle_data = get_egg_cycle_statistics(historical_data)
    egg_cycle_data_hour = get_egg_cycle_statistics_by_hour(historical_data)

    data = {
        'historical_data': historical_data,
        'egg_cycle_data': egg_cycle_data,
        'egg_cycle_data_hour':egg_cycle_data_hour,
        'lock_down_date': lock_down_date.strftime("%m-%d-%Y"),
        'hatch_date': hatch_date.strftime("%m-%d-%Y"),
        'current_data': current_data,  # Add current data to the dictionary
    }
    return render_template('index.html', data=data)

@app.route('/historical_data')
def historical_data():
    cursor = incubator.find().sort("Timestamp", -1).limit(50)
    historical_data = []
    for data in cursor:
        historical_data.append({
            'Time': data['Timestamp'].strftime('%m-%d-%Y %H:%M'),
            'Temperature(F)': data['Temperature(F)'],
            'Temperature Relay Status': data['Temperature Relay Status'],
            'Humidity(%)': data['Humidity(%)'],
            'Humidity Relay Status': data['Humidity Relay Status'],
            'Last Egg Turn': data['Last Egg Turn'],
            'Day in Egg Cycle': data['Day in Egg Cycle']
        })
    return render_template('historical_data.html', historical_data=historical_data)

@app.context_processor
def inject_nav_links():
    return {'nav_links': [{'url': '/', 'label': 'Home'}, {'url': '/historical_data', 'label': 'Historical Data'}]}


def get_egg_cycle_statistics(historical_data):
    egg_cycle_dict = {}
    for data in historical_data:
        day = data['Day in Egg Cycle']
        temperature = data['Temperature(F)']
        humidity = data['Humidity(%)']
        if day in egg_cycle_dict:
            egg_cycle_dict[day]['temperature'].append(temperature)
            egg_cycle_dict[day]['humidity'].append(humidity)
        else:
            egg_cycle_dict[day] = {
                'temperature': [temperature],
                'humidity': [humidity],
            }
    
    egg_cycle_statistics = []
    for day, values in egg_cycle_dict.items():
        avg_temp = np.mean(values['temperature'])
        std_temp = np.std(values['temperature'])
        avg_hum = np.mean(values['humidity'])
        std_hum = np.std(values['humidity'])
        egg_cycle_statistics.append({
            'Day in Egg Cycle': day,
            'Average Temperature (F)': round(avg_temp, 2),
            'Temperature Standard Deviation': round(std_temp, 2),
            'Average Humidity (%)': round(avg_hum, 2),
            'Humidity Standard Deviation': round(std_hum, 2),
        })
        
    egg_cycle_statistics.sort(key=lambda x: x['Day in Egg Cycle'], reverse=True)
    return egg_cycle_statistics



def get_egg_cycle_statistics_by_hour(historical_data):
    egg_cycle_dict = {}
    for data in historical_data:
        day = data['Day in Egg Cycle']
        temperature = data['Temperature(F)']
        humidity = data['Humidity(%)']
        timestamp = data['Time']
        hour = floor(timestamp.timestamp() / 3600)
        if day in egg_cycle_dict:
            if hour in egg_cycle_dict[day]:
                egg_cycle_dict[day][hour]['temperature'].append(temperature)
                egg_cycle_dict[day][hour]['humidity'].append(humidity)
            else:
                egg_cycle_dict[day][hour] = {
                    'temperature': [temperature],
                    'humidity': [humidity],
                }
        else:
            egg_cycle_dict[day] = {
                hour: {
                    'temperature': [temperature],
                    'humidity': [humidity],
                }
            }
    
    egg_cycle_statistics = []
    for day, hours in egg_cycle_dict.items():
        for hour, values in hours.items():
            avg_temp = np.mean(values['temperature'])
            std_temp = np.std(values['temperature'])
            avg_hum = np.mean(values['humidity'])
            std_hum = np.std(values['humidity'])
            timestamp = datetime.fromtimestamp(hour * 3600)
            egg_cycle_statistics.append({
                'Time': timestamp.strftime('%m-%d-%Y %H:%M %p'),
                'Average Temperature (F)': round(avg_temp, 2),
                'Temperature Standard Deviation': round(std_temp, 2),
                'Average Humidity (%)': round(avg_hum, 2),
                'Humidity Standard Deviation': round(std_hum, 2),
            })
        
    egg_cycle_statistics.sort(key=lambda x: x['Time'], reverse=True)
    return egg_cycle_statistics



if __name__ == "__main__":

    app.run(debug=True, host='0.0.0.0', port=8000)
    
