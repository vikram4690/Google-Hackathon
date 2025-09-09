import os
import json
import vertexai
from flask import Flask, request, jsonify, render_template, session, redirect, url_for, flash
from flask_cors import CORS
from vertexai.generative_models import GenerativeModel

# --- Initialization ---
app = Flask(__name__, template_folder='templates')
CORS(app) # Enable Cross-Origin Resource Sharing
# A SECRET_KEY is required to use sessions in Flask
app.config['SECRET_KEY'] = 'your-super-secret-key-change-this'

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

@app.route('/itinerary')
def show_itinerary():
    """Displays the generated itinerary from the session."""
    itinerary_data = session.get('itinerary_data', None)
    return render_template('itinerary.html', itinerary_data=itinerary_data)

@app.route('/regenerate', methods=['POST'])
def regenerate_itinerary():
    """Receives an existing itinerary and a change request, then regenerates."""
    original_itinerary_json = request.form.get('original_itinerary')
    change_request = request.form.get('change_request')

    if not original_itinerary_json or not change_request:
        # Flash a helpful message to the user
        flash('Please enter your requested changes in the text box before regenerating.', 'error')
        # Redirect the user back to the itinerary page
        return redirect(url_for('show_itinerary'))

    # Convert the JSON string from the form back into a Python dictionary
    original_data = json.loads(original_itinerary_json)
    original_plan = original_data.get('itinerary', {})
    user_request = original_data.get('request', {})

    # Create a new, more specific prompt for regeneration
    prompt = f"""
    Act as an expert travel agent who is revising an existing plan based on customer feedback.
    Your task is to modify the provided itinerary according to the user's change request.
    Preserve the structure and details of the original plan for parts that were not mentioned in the request.

    Original User Request Details:
    - Trip Origin: {user_request.get('source')}
    - Destination: {user_request.get('destination')}
    - Dates: {user_request.get('start_date')} to {user_request.get('return_date')}
    - Budget: Approximately {user_request.get('budget')} INR
    - Interests: {', '.join(user_request.get('interests', []))}
    - Transport: {user_request.get('transport_mode')}

    The Original Itinerary (as a JSON object):
    {json.dumps(original_plan, indent=2)}

    User's Specific Change Request:
    "{change_request}"

    Your response MUST be the complete, updated itinerary as a valid JSON object with the exact same structure as the original.
    Do not add any text before or after the JSON object.
    The language of the response must be {user_request.get('language', 'English')}.
    """

    try:
        response = model.generate_content(prompt)
        cleaned_text = response.text.strip().replace("```json", "").replace("```", "")
        ai_generated_itinerary = json.loads(cleaned_text)

        final_response = {"request": user_request, "itinerary": ai_generated_itinerary}

        # Update the session with the new, regenerated itinerary
        session['itinerary_data'] = final_response

        # Redirect the user back to the itinerary page to see the changes
        return redirect(url_for('show_itinerary'))

    except Exception as e:
        print(f"An error occurred during regeneration: {e}")
        return f"An error occurred during regeneration: {e}", 500

# --- Future Placeholder Routes ---
@app.route('/login')
def login():
    # In the future, this will render a login.html template
    return "Login Page (Coming Soon)"

@app.route('/signup')
def signup():
    # In the future, this will render a signup.html template
    return "Sign-up Page (Coming Soon)"

@app.route('/payment')
def payment():
    # In the future, this will render a payment.html template
    return "Payment Page (Coming Soon)"

@app.route('/confirmation')
def confirmation():
    # In the future, this will render a confirmation.html template
    return "Booking Confirmation Page (Coming Soon)"

@app.route('/plan', methods=['POST'])
def plan_trip():
    """Receives form data, generates an itinerary, saves it to the session, and redirects."""
    # This now reads from a standard form, not a JSON request
    data = {
        "source": request.form.get('source'),
        "destination": request.form.get('destination'),
        "start_date": request.form.get('start_date'),
        "return_date": request.form.get('return_date'),
        "budget": request.form.get('budget'),
        "interests": request.form.getlist('interests'), # Gets all checkbox values
        "transport_mode": request.form.get('transport_mode'),
        "language": request.form.get('language'),
        "additional_reqs": request.form.get('additional_reqs')
    }

    # The prompt construction is the same as before
    prompt = f"""
    Act as an expert travel agent specializing in personalized trips within India.
    Your task is to create a detailed, day-by-day travel itinerary based on the user's specific requirements.

    User Request Details:
    - Trip Origin: {data.get('source')}
    - Destination: {data.get('destination')}
    - Start Date: {data.get('start_date')}
    - Return Date: {data.get('return_date')}
    - Primary Mode of Transport: {data.get('transport_mode')}
    - Total Budget: Approximately {data.get('budget')} INR
    - Key Interests: {', '.join(data.get('interests', []))}
    - Additional Requirements: {data.get('additional_reqs', 'None')}
    - Itinerary Language: {data.get('language', 'English')}

    Your response MUST be a valid JSON object with the following structure and nothing else.
    {{
      "plan": [
        {{
          "day": <day_number>, "date": "<The calculated date for this day>", "theme": "<a creative theme for the day>",
          "activities": [ {{"time": "<e.g., 9:00 AM - 11:00 AM>", "description": "<detailed activity description>", "location_name": "<name of place>"}} ]
        }}
      ],
      "cost_breakdown": {{
        "accommodation_estimate_inr": <estimated_cost>, "transport_estimate_inr": <estimated_cost>,
        "activities_estimate_inr": <estimated_cost>, "food_estimate_inr": <estimated_cost>,
        "total_estimate_inr": <total_estimated_cost>
      }}
    }}
    Ensure all text is in the requested language: {data.get('language', 'English')}.
    """

    try:
        response = model.generate_content(prompt)
        cleaned_text = response.text.strip().replace("```json", "").replace("```", "")
        ai_generated_itinerary = json.loads(cleaned_text)

        final_response = {"request": data, "itinerary": ai_generated_itinerary}

        # Save the complete itinerary data to the user's session
        session['itinerary_data'] = final_response

        # Redirect the user's browser to the new /itinerary page
        return redirect(url_for('show_itinerary'))

    except Exception as e:
        print(f"An error occurred: {e}")
        # In a real app, you would redirect to an error page
        return f"An error occurred: {e}", 500

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

