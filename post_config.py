import os
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
load_dotenv()

POSTGRES_DB = os.getenv("POSTGRES_DB", "omni_voice_db")
POSTGRES_USER = os.getenv("POSTGRES_USER","postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD","12345")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", 5432)

DB_CONNECTION = {
        "dbname":POSTGRES_DB,
        "user":POSTGRES_USER,
        "password":POSTGRES_PASSWORD,
        "host":POSTGRES_HOST,
        "port":POSTGRES_PORT,
        "cursor_factory":RealDictCursor
        }