import joblib
import numpy as np
from langchain.agents import initialize_agent, Tool
from langchain.llms import HuggingFaceHub

# --- Load Model ---
model = joblib.load("fare_predictor.pkl")

# --- Define Prediction Function ---
def predict_fare(trip_distance: float, passenger_count: int,
                 trip_duration_minutes: float, avg_speed_mph: float,
                 rate_code_id: int, payment_type: int) -> float:
    features = np.array([[trip_distance, passenger_count,
                          trip_duration_minutes, avg_speed_mph,
                          rate_code_id, payment_type]])
    pred = model.predict(features)[0]
    return round(float(pred), 2)

# --- Wrap as Tool ---
def fare_tool_func(query: dict) -> str:
    try:
        # Extracting parameters from the query
        trip_distance = query.get("trip_distance", 0.0)
        passenger_count = query.get("passenger_count", 1)
        trip_duration_minutes = query.get("trip_duration_minutes", 0.0)
        avg_speed_mph = query.get("avg_speed_mph", 0.0)
        rate_code_id = query.get("rate_code_id", 1)
        payment_type = query.get("payment_type", 1)
        
        # Get predicted fare
        fare = predict_fare(trip_distance, passenger_count, 
                            trip_duration_minutes, avg_speed_mph, 
                            rate_code_id, payment_type)
        return f"Predicted fare: ${fare}"
    except Exception as e:
        return f"Error predicting fare: {str(e)}"

fare_tool = Tool(
    name="Fare Predictor",
    func=fare_tool_func,
    description="Predicts NYC taxi fare. Expects a dictionary with keys: trip_distance, passenger_count, trip_duration_minutes, avg_speed_mph, rate_code_id, payment_type."
)

# --- Initialize Agent ---
llm = HuggingFaceHub(repo_id="EleutherAI/gpt-neo-2.7B", model_kwargs={"temperature": 0.7})  # Replace Ollama with HuggingFace LLM
agent = initialize_agent([fare_tool], llm, agent="zero-shot-react-description", verbose=True)

# --- Example Query ---
query = {
  "trip_distance": 5.0,
  "passenger_count": 2,
  "trip_duration_minutes": 15,
  "avg_speed_mph": 20,
  "rate_code_id": 1,
  "payment_type": 1
}

# Wrap the query in a dictionary with the 'input' key
response = agent.run({"input": query})
print(response)
