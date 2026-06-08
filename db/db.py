import os
from dotenv import load_dotenv, find_dotenv
from peewee_async import MySQLDatabase, AioModel

load_dotenv(find_dotenv()) 

db_manager =MySQLDatabase(
    os.getenv('DB_DATABASE'),
    user=os.getenv('DB_USERNAME'),
    password=os.getenv('DB_PASSWORD'),
    host=os.getenv('DB_HOST'),
    port=int(os.getenv('DB_PORT'))
)


class BaseModel(AioModel):
    class Meta:
        database = db_manager