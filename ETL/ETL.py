import pandas as pd
from sqlalchemy import create_engine,text
from dotenv import load_dotenv
import  urllib.parse
import os

# Load environment variables from .env
load_dotenv()

# Fetch variables
USER = os.getenv("user")
PASSWORD = urllib.parse.quote_plus(os.getenv("password"))
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")


# Construct the SQLAlchemy connection string
DATABASE_URL = f"postgresql+psycopg2://{USER}:{PASSWORD}@{HOST}:{PORT}/{DBNAME}?sslmode=require"
def load_data_from_csv(file_path):
    """
    Load data from a CSV file into a pandas DataFrame.
    """
    try:
        df = pd.read_csv(file_path)
        print(f"Data loaded successfully from {file_path}")
        return df
    except Exception as e:
        print(f"Error loading data from {file_path}: {e}")
        return None


def load_data_to_postgres( table_name):
    """
    Load a pandas DataFrame into a PostgreSQL table.
    """

    # Create the SQLAlchemy engine
    engine = create_engine(DATABASE_URL)
    try:
        with engine.connect() as connection:
            print("Connection successful!")

            #truncate table if exists
            connection.execute(text(f"TRUNCATE TABLE public.\"{table_name}\";")) 
            print(f"Table {table_name} truncated successfully.")
            # Load data in chunks to handle large files
            chunksize = 100_000 # adjust based on RAM
            for i, chunk in enumerate(pd.read_csv(r'C:\Work\Personal\myenv\ETL\data\yellow_tripdata_2015-01.csv', chunksize=chunksize)):
                if i<= 12:
                    print(f"Loading chunk {i} ...")
                    chunk.to_sql(table_name, con=connection, if_exists='append', index=False)
                else:
                    break
        
            print(f"Data loaded into {table_name} successfully.")
    except Exception as e:
        print(f"Failed to connect: {e}")
        
if __name__ == "__main__":
    load_data_to_postgres('Texi_data')