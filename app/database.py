from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = MongoClient(MONGO_URI)
db = client.digital_loyalty_card  # Database will be created automatically

vendors_collection = db.vendors 
customers_collection = db.customers