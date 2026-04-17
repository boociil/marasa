from peewee import *
import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv()) 

db = MySQLDatabase(
    os.getenv('DB_DATABASE'),
    user=os.getenv('DB_USERNAME'),
    password=os.getenv('DB_PASSWORD'),
    host=os.getenv('DB_HOST'),
    port=int(os.getenv('DB_PORT'))
)

class BaseModel(Model):
    class Meta:
        database = db