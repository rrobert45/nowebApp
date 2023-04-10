import time
import RPi.GPIO as GPIO
from pymongo import MongoClient
import pymongo
from datetime import datetime, timedelta
import json
import board
import adafruit_ahtx0


with open('/home/robert/Desktop/config.json') as config_file:
    config = json.load(config_file)

start_date = datetime.strptime(config['start_date'], '%Y-%m-%d')


# Set the sensor type (DHT22) and the GPIO pin number
i2c = board.I2C()
sensor = adafruit_ahtx0.AHTx0(i2c)

# Set the relay pin number
egg_turner_relay_pin = 19
heat_relay_pin = 21
humidifier_relay_pin = 20

# Set the interval for logging data and turning on the relay (in seconds)
log_interval = config['log_interval']
relay_interval = config['relay_interval']
roll_interval = config['roll_interval']
last_relay_on = config['last_relay_on']
temperature_relay_status = config['temperature_relay_status']
humidity_relay_status = config['humidity_relay_status']



# Set the temperature and humidity thresholds
temperature_threshold = 100
humidity_threshold = 35

# Initialize the GPIO pins
GPIO.setmode(GPIO.BCM)
GPIO.setup(heat_relay_pin, GPIO.OUT)
GPIO.setup(humidifier_relay_pin, GPIO.OUT)
GPIO.setup(egg_turner_relay_pin, GPIO.OUT)


def mongoDB():
    # Connect to MongoDB
    uri = config['uri']
    client = MongoClient(uri)
    db = client[config['database']]
    incubator = db[config['collection']]

    return client,incubator

def read_and_log_data():
    global temperature_relay_status
    global humidity_relay_status
    
    while True:
        try:
            day_in_cycle = day(start_date)
            temperature, humidity = control()
            last_relay_on = eggTurner(day_in_cycle)
            log_data(temperature, humidity, last_relay_on, temperature_relay_status, humidity_relay_status, day_in_cycle)

            time.sleep(10)
            
        except KeyboardInterrupt:
            break
        except:
            print("An error occurred. Retrying in 30 seconds...")
            time.sleep(5)
            continue
    # Clean up the GPIO pins
    GPIO.cleanup()
    # Close the MongoDB connection
    

def day(start_date):
    global humidity_threshold
    current_date = datetime.now()
    total_days = 21
    day_in_cycle = (current_date - start_date).days % total_days
    #if day_in_cycle >= 18:
        #humidity_threshold = 65
    return day_in_cycle



def control():
    global temperature_relay_status
    global humidity_relay_status
    global temperature_threshold
    global humidity_threshold
    temperature, humidity = read_sensor_data()
    if temperature < temperature_threshold:
        # Turn on the heat source
        GPIO.output(heat_relay_pin, GPIO.LOW)
        if GPIO.input(heat_relay_pin) == GPIO.LOW:
            temperature_relay_status = "ON"
    elif temperature > temperature_threshold + .5:
        # Turn off the heat source
        GPIO.output(heat_relay_pin, GPIO.HIGH)
        if GPIO.input(heat_relay_pin) == GPIO.HIGH:
            temperature_relay_status = "OFF"
    else:
        # Do nothing
        if GPIO.input(heat_relay_pin) == GPIO.LOW:
            temperature_relay_status = "ON"
        if GPIO.input(heat_relay_pin) == GPIO.HIGH:
            temperature_relay_status = "OFF"

    if humidity < humidity_threshold:
        # Turn on the humidifier
        GPIO.output(humidifier_relay_pin, GPIO.LOW)
        if GPIO.input(humidifier_relay_pin) == GPIO.LOW:
            humidity_relay_status = "ON"
    elif humidity > humidity_threshold + 5:
        # Turn off the humidifier
        GPIO.output(humidifier_relay_pin, GPIO.HIGH)
        if GPIO.input(humidifier_relay_pin) == GPIO.HIGH:
            humidity_relay_status = "OFF"
    else:
        # Do nothing
        if GPIO.input(humidifier_relay_pin) == GPIO.LOW:
            humidity_relay_status = "ON"
        if GPIO.input(humidifier_relay_pin) == GPIO.HIGH:
            humidity_relay_status = "OFF"

    return temperature, humidity

def read_sensor_data():
    # Read the humidity and temperature
    humidity, temperature = sensor.relative_humidity, sensor.temperature
    if humidity is not None and temperature is not None:
        temperature = (temperature * 9/5) + 32
        return round(temperature,2), round(humidity,1)
    else:
        print('Failed to read data from sensor')
        return None, None

def eggTurner(day_in_cycle):
    global last_relay_on
    
    current_time = datetime.now()
    if day_in_cycle < 18:
        if last_relay_on is None:
            last_relay_on = datetime.now()
        if GPIO.input(egg_turner_relay_pin) == 1:
            if current_time - last_relay_on >= timedelta(seconds=relay_interval):
                # Turn on the relay for 2 minutes
                GPIO.output(egg_turner_relay_pin, GPIO.LOW)
                last_relay_on = current_time
        elif GPIO.input(egg_turner_relay_pin) == 0:        
            if current_time - last_relay_on >= timedelta(seconds=roll_interval):
                GPIO.output(egg_turner_relay_pin, GPIO.HIGH)
    return last_relay_on

def log_data(temperature, humidity, last_relay_on, temperature_relay_status, humidity_relay_status, day_in_cycle):
    timestamp = datetime.now()
    date = timestamp.strftime("%m-%d-%Y %H:%M:%S")
    try:
        client,incubator = mongoDB()
        
        data = {
            'Timestamp' : timestamp,
            #'Time': time.strftime("%m-%d-%Y %H:%M"),
            'Temperature(F)': temperature,
            'Temperature Relay Status': temperature_relay_status,
            'Humidity(%)': humidity,
            'Humidity Relay Status': humidity_relay_status,
            'Last Egg Turn': last_relay_on.strftime("%m-%d-%Y %I:%M %P") if last_relay_on is not None else '',
            'Day in Egg Cycle': day_in_cycle
        }
        # Insert the data into the incubator collection
        incubator.insert_one(data)
        
        print(f'{date}: temperature = {temperature}     humidity = {humidity}       Day in Cycle = {day_in_cycle}  Temperature Relay = {temperature_relay_status}' )
        client.close()
    except:
        print(f'Data log failed on {date}')





if __name__ == "__main__":
    read_and_log_data()