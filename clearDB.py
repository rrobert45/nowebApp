from pymongo import MongoClient

with open('/home/robert/Desktop/config.json') as config_file:
    config = json.load(config_file)

# Connect to MongoDB
uri = config['uri']
client = MongoClient(uri)
db = client[config['database']]
incubator = db[config['collection']]

# Clear the incubator collection
incubator.delete_many({})

# Close the MongoDB connection
client.close()