import os
import json
import vertexai
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from vertexai.generative_models import GenerativeModel

# --- Initialization ---
app = Flask(__name__, template_folder='templates')
CORS(app) # Enable Cross-Origin Resource Sharing

# --- Configuration (Best Practice: Read from Environment Variables) ---
VERTEX_PROJECT = os.environ.get('GOOGLE_PROJECT_ID')
VERTEX_LOCATION = 'asia-south1' # Mumbai region, as it supports the model

if not VERTEX_PROJECT:
    raise ValueError("Missing GOOGLE_PROJECT_ID environment variable.")

# --- Client Initialization ---
try:
    # Explicitly initialize the Vertex AI SDK for the correct project and location
    vertexai.init(project=VERTEX_PROJECT, location=VERTEX_LOCATION)
    # Load the Gemini Pro model
    model = GenerativeModel("gemini-1.5-flash-002")
except Exception as e:
    raise RuntimeError(f"Failed to initialize Vertex AI Model: {e}")

# --- API ROUTES ---

@app.route('/')
def index():
    """Serves the frontend HTML file from the 'templates' folder."""
    return render_template('index.html')

@app.route('/plan', methods=['POST'])
def plan_trip():
    """Generates a personalized trip itinerary using Gemini."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON input"}), 400

    # Construct a detailed prompt for the AI
    prompt = f"""
    Act as an expert travel agent for trips in India. Your task is to create a personalized, day-by-day travel itinerary.

    User Request:
    - Destination: {data.get('location')}
    - Duration: {data.get('duration')} days
    - Budget: Approximately {data.get('budget')} INR
    - Interests: {', '.join(data.get('interests'))}
    - Response Language: {data.get('language', 'en')}

    Your response MUST be a valid JSON object with the following structure and nothing else. Do not wrap it in markdown like ```json.
    {{
      "plan": [
        {{
          "day": <day_number>,
          "theme": "<a creative theme for the day>",
          "activities": [
            {{
              "time": "<e.g., 9:00 AM - 11:00 AM>",
              "description": "<detailed activity description, including why it fits the user's interests>",
              "location_name": "<name of the specific place or landmark>"
            }}
          ]
        }}
      ],
      "cost_breakdown": {{
        "accommodation_estimate_inr": <estimated_cost_in_inr>,
        "transport_estimate_inr": <estimated_cost_in_inr>,
        "activities_estimate_inr": <estimated_cost_in_inr>,
        "food_estimate_inr": <estimated_cost_in_inr>,
        "total_estimate_inr": <total_estimated_cost>
      }}
    }}
    Ensure all text in the response (themes, descriptions) is in the requested language: {data.get('language', 'en')}.
    """

    try:
        # Call the Gemini API
        response = model.generate_content(prompt)
        # Clean up the response to ensure it's a valid JSON string
        cleaned_text = response.text.strip().replace("```json", "").replace("```", "")
        ai_generated_itinerary = json.loads(cleaned_text)

        # Combine with user data for a full response
        final_response = {
            "request": data,
            "itinerary": ai_generated_itinerary
        }
        return jsonify(final_response)

    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": "Failed to generate itinerary.", "details": str(e)}), 500

@app.route('/book', methods=['POST'])
def book_trip():
    """Mock endpoint for booking and payment."""
    confirmation = {
        "status": "success",
        "message": "Booking confirmed! (This is a mock confirmation for the prototype)",
        "booking_id": f"EMT-MOCK-{os.urandom(4).hex().upper()}"
    }
    return jsonify(confirmation)

@app.route('/adjust', methods=['POST'])
def adjust_itinerary():
    """Mock endpoint for real-time adjustments."""
    data = request.get_json()
    change_request = data.get('change_request', 'No changes requested.')
    response = {
        "status": "adjusted",
        "message": f"Adjustment request for '{change_request}' received. (This is a mock response)"
    }
    return jsonify(response)

if __name__ == '__main__':
    # This configuration is compatible with Cloud Run
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)), debug=True)

