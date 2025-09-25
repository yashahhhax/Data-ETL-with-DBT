import streamlit as st
import joblib
import numpy as np
import re
import json
import traceback
from langchain.agents import initialize_agent, Tool
from langchain_community.llms import Ollama
import os

# ----------------------------
# Load ML Model
# ----------------------------
model = joblib.load("fare_predictor.pkl")

def predict_fare(trip_distance: float, passenger_count: int,
                 trip_duration_minutes: float, avg_speed_mph: float,
                 rate_code_id: int, payment_type: int) -> float:
    features = np.array([[trip_distance, passenger_count,
                          trip_duration_minutes, avg_speed_mph,
                          rate_code_id, payment_type]])
    pred = model.predict(features)[0]
    return round(float(pred), 2)

# ----------------------------
# Helpers: parse text / JSON
# ----------------------------
def parse_nl_trip(text: str):
    """
    Heuristic parser extracting up to 6 numeric values from freeform text.
    Mapping: [trip_distance, passenger_count, trip_duration_minutes, avg_speed_mph, rate_code_id, payment_type]
    Returns (parsed_dict, defaults_used_list)
    """
    nums = re.findall(r'\d+(?:\.\d+)?', text)
    nums = [float(n) for n in nums]
    defaults = []

    trip_distance = nums[0] if len(nums) >= 1 else None
    passenger_count = int(nums[1]) if len(nums) >= 2 else None
    trip_duration = nums[2] if len(nums) >= 3 else None
    avg_speed = nums[3] if len(nums) >= 4 else None
    rate_code_id = int(nums[4]) if len(nums) >= 5 else 1
    payment_type = int(nums[5]) if len(nums) >= 6 else 1

    # sensible defaults & simple inference
    if trip_distance is None:
        trip_distance = 5.0
        defaults.append("trip_distance=5.0 (default)")
    if passenger_count is None:
        passenger_count = 1
        defaults.append("passenger_count=1 (default)")
    if trip_duration is None and trip_distance is not None and avg_speed is not None:
        trip_duration = (trip_distance / avg_speed) * 60.0
        defaults.append("trip_duration inferred from distance and speed")
    if trip_duration is None:
        trip_duration = 15.0
        defaults.append("trip_duration=15 (default)")
    if avg_speed is None:
        # compute avg_speed from distance & duration
        try:
            avg_speed = trip_distance / (trip_duration / 60.0)
            defaults.append("avg_speed inferred")
        except Exception:
            avg_speed = 20.0
            defaults.append("avg_speed=20 (default)")

    parsed = {
        "trip_distance": float(trip_distance),
        "passenger_count": int(passenger_count),
        "trip_duration_minutes": float(trip_duration),
        "avg_speed_mph": float(avg_speed),
        "rate_code_id": int(rate_code_id),
        "payment_type": int(payment_type),
    }
    return parsed, defaults

def try_parse_json(input_text: str):
    """
    Try to parse a JSON object from input_text. Return dict or raise.
    """
    try:
        obj = json.loads(input_text)
        if not isinstance(obj, dict):
            raise ValueError("JSON input must be an object/dict.")
        return obj
    except Exception:
        raise

# ----------------------------
# Tool: robust fare predictor (accepts JSON or plain text)
# ----------------------------
def fare_predictor_tool(input_text: str) -> str:
    """
    Accepts either:
      - a JSON string with required keys, OR
      - free text like "10 miles, 3 passengers, 20 minutes"
    Returns a friendly string (no stack traces).
    """
    try:
        # 1) Try JSON first
        try:
            data = try_parse_json(input_text)
            # ensure required keys exist (and coerce types)
            required = ["trip_distance", "passenger_count", "trip_duration_minutes", "avg_speed_mph", "rate_code_id", "payment_type"]
            missing = [k for k in required if k not in data]
            defaults = []
            if missing:
                # if JSON missing keys, try to fill using NLP parser fallback
                parsed, parsed_defaults = parse_nl_trip(input_text)
                # merge: prefer values from JSON, else from parsed
                for k in required:
                    if k not in data or data[k] in (None, ""):
                        data[k] = parsed[k]
                        defaults += parsed_defaults
            else:
                # coerce types:
                data = {
                    "trip_distance": float(data["trip_distance"]),
                    "passenger_count": int(data["passenger_count"]),
                    "trip_duration_minutes": float(data["trip_duration_minutes"]),
                    "avg_speed_mph": float(data["avg_speed_mph"]),
                    "rate_code_id": int(data["rate_code_id"]),
                    "payment_type": int(data["payment_type"]),
                }
        except Exception:
            # 2) Fallback: parse natural language
            data, defaults = parse_nl_trip(input_text)

        # Validate minimally
        if data["trip_distance"] <= 0 or data["trip_duration_minutes"] <= 0:
            return "⚠️ I couldn't use those values — trip distance and duration must be > 0. Try: '10 miles, 3 passengers, 20 minutes'."

        # Predict
        pred = predict_fare(
            data["trip_distance"],
            data["passenger_count"],
            data["trip_duration_minutes"],
            data["avg_speed_mph"],
            data["rate_code_id"],
            data["payment_type"]
        )
        msg = f"Predicted fare: ${pred}"
        if defaults:
            msg += f"  (used defaults/inferences: {', '.join(defaults)})"
        return msg

    except Exception as e:
        # Friendly error for users
        return ("⚠️ Sorry — I couldn't compute a fare for that request. "
                "Please provide either:\n"
                "  • Plain text: '10 miles, 3 passengers' or\n"
                "  • JSON: {\"trip_distance\": 10, \"passenger_count\": 3, \"trip_duration_minutes\": 20, \"avg_speed_mph\": 25, \"rate_code_id\": 1, \"payment_type\": 1}\n"
                f"\n(Technical: {str(e)})"
               )

fare_tool = Tool(
    name="Fare Predictor",
    func=fare_predictor_tool,
    description=("Predicts NYC taxi fare. Input may be plain text like '10 miles, 3 passengers' "
                 "or JSON with keys: trip_distance, passenger_count, trip_duration_minutes, avg_speed_mph, rate_code_id, payment_type.")
)

# ----------------------------
# LLM + Agent (Ollama)
# ----------------------------
llm = Ollama()  # adjust model arg if needed
agent = initialize_agent([fare_tool], llm, agent="zero-shot-react-description", verbose=False)

# ----------------------------
# Streamlit UI
# ----------------------------
st.set_page_config(page_title="NYC Taxi AI", layout="wide")
st.title("🚖 NYC Taxi AI Assistant")

option = st.sidebar.radio("Choose Mode:", ["Fare Prediction", "Chat with Data"])

# --- Fare Prediction Page (direct form) ---
if option == "Fare Prediction":
    st.header("🔮 Fare Prediction")
    col1, col2 = st.columns(2)

    with col1:
        trip_distance = st.number_input("Trip Distance (miles)", 0.1, 200.0, 5.0)
        passenger_count = st.number_input("Passenger Count", 1, 10, 2)
        trip_duration_minutes = st.number_input("Trip Duration (minutes)", 1.0, 600.0, 15.0)

    with col2:
        avg_speed_mph = st.number_input("Average Speed (mph)", 1.0, 120.0, 20.0)
        rate_code_id = st.selectbox("Rate Code ID", [1, 2, 3, 4, 5, 6], index=0)
        payment_type = st.selectbox("Payment Type", [1, 2], index=0)  # 1=Credit, 2=Cash, etc.

    if st.button("Predict Fare"):
        fare = predict_fare(trip_distance, passenger_count, trip_duration_minutes,
                            avg_speed_mph, rate_code_id, payment_type)
        st.success(f"💰 Estimated Fare: ${fare}")

# --- Chat with Data Page ---
else:
    st.header("💬 Chat with Your Taxi Data")
    user_query = st.text_area("Ask me something:", placeholder="e.g., Predict fare for a 10-mile trip with 3 passengers")

    if st.button("Ask"):
        if user_query.strip():
            with st.spinner("Thinking..."):
                try:
                    # If it's a straightforward fare request, handle locally for reliability:
                    if re.search(r'predict.*fare|fare for|estimate.*fare', user_query, re.I):
                        parsed, defaults = parse_nl_trip(user_query)
                        if parsed["trip_distance"] is None or parsed["passenger_count"] is None:
                            st.error("Couldn't extract trip distance or passenger count. Try: '10 miles, 3 passengers' or provide JSON.")
                        else:
                            fare = predict_fare(parsed["trip_distance"], parsed["passenger_count"],
                                                parsed["trip_duration_minutes"], parsed["avg_speed_mph"],
                                                parsed["rate_code_id"], parsed["payment_type"])
                            msg = f"💰 Predicted fare: ${fare}"
                            if defaults:
                                msg += f"  (used defaults/inferences: {', '.join(defaults)})"
                            st.success(msg)
                    else:
                        # Otherwise, let the agent (LLM) handle it; agent may call the fare tool if needed.
                        response = agent.run(user_query)
                        st.write("🤖 Agent Response:")
                        st.info(response)

                except Exception as e:
                    st.error("Sorry — I couldn't complete that request. Try phrasing like 'Predict fare for a 10-mile trip with 3 passengers' or provide JSON.")
                    with st.expander("Show technical details"):
                        st.text(traceback.format_exc())
