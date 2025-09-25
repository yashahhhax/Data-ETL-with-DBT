import pandas as pd
import psycopg2
from sqlalchemy import create_engine
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error
import joblib
import os
from dotenv import load_dotenv
import  urllib.parse
import datetime

load_dotenv()

USER = os.getenv("user")
PASSWORD = urllib.parse.quote_plus(os.getenv("password"))
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")

# --- Connect to Supabase Postgres ---
engine = create_engine(
    f"postgresql+psycopg2://{USER}:{PASSWORD}@{HOST}:{PORT}/{DBNAME}?sslmode=require"
)

query = """
    SELECT trip_distance, passenger_count, trip_duration_minutes, avg_speed_mph,
           rate_code_id, payment_type, fare_amount
    FROM bi.core_texi
    WHERE fare_amount > 0
    AND trip_distance > 0
    AND trip_duration_minutes > 0 limit 100000
"""
df = pd.read_sql(query, engine)
print(f"Data shape: {df.shape}")
# --- Features & Target ---
X = df.drop(columns=["fare_amount"])
y = df["fare_amount"]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
print("Model training data shape:", X_train.shape)
start_time = datetime.datetime.now()
# --- Train model ---
model = RandomForestRegressor(n_estimators=200, random_state=42)
model.fit(X_train, y_train)
total_time = datetime.datetime.now() - start_time
print("Training took:", total_time.total_seconds(), "seconds")
print("Model trained.")

# --- Evaluate ---
y_pred = model.predict(X_test)
print("RMSE:", mean_squared_error(y_test, y_pred))

# --- Save model ---
joblib.dump(model, "fare_predictor.pkl")

