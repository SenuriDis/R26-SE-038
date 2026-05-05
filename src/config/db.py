import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "static_code_analysis_db")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

analysis_collection = db["analysis_results"]