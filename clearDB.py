from pymongo import MongoClient
import json

with open('config.json') as config_file:
    config = json.load(config_file)

# Connect to MongoDB
uri = config['uri']
client = MongoClient(uri)
db = client[config['database']]
incubator = db[config['collection']]

# Clear the incubator collection
incubator.drop()

# Close the MongoDB connection
client.close()