import asyncio
import json
from kasa import SmartPlug
from pymongo import MongoClient
import time

# Load MongoDB configuration from a JSON file
with open('config.json') as config_file:
    config = json.load(config_file)

# Replace with the IP address of your Kasa smart plug
smart_plug_ip = "192.168.1.167"

# Connect to MongoDB
uri = config['uri']
client = MongoClient(uri)
db = client[config['database']]
incubator = db[config['collection']]

async def turn_on_kasa_smart_plug(ip: str):
    plug = SmartPlug(ip)
    await plug.update()
    await plug.turn_on()

async def turn_off_kasa_smart_plug(ip: str):
    plug = SmartPlug(ip)
    await plug.update()
    await plug.turn_off()

async def main():
    while True:
        try:
            # Fetch the latest temperature record from the database
            latest_record = incubator.find().sort("_id", -1).limit(1)[0]
            temperature_f = latest_record['Temperature(F)']
            printTime = latest_record['Timestamp']

            if temperature_f > 102.5:
                # Turn off the plug
                await turn_off_kasa_smart_plug(smart_plug_ip)
                await asyncio.sleep(30)  # Wait for 30 seconds

                # Turn on the plug
                await turn_on_kasa_smart_plug(smart_plug_ip)

            print(f"{printTime} -- Temperature {temperature_f}")
        except:
            print("An error occurred while fetching the latest temperature record from the database. Retrying in 30 seconds...")
            await asyncio.sleep(30)  # Wait for 30 seconds and try again

        await asyncio.sleep(120)  # Wait for 2 minutes before checking again

if __name__ == "__main__":
    asyncio.run(main())