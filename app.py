import os
from dotenv import load_dotenv
import json
import vertexai
from flask import Flask, request, jsonify, render_template, session, redirect, url_for, flash
from flask_cors import CORS
from vertexai.generative_models import GenerativeModel, Tool, FunctionDeclaration, Part
import googlemaps
import firebase_admin
from firebase_admin import credentials, auth, firestore
import requests
from datetime import datetime, date, timedelta



load_dotenv()
# --- Initialization ---
app = Flask(__name__, template_folder='templates')
app.secret_key = 'your-very-secret-key-for-hackathon'
CORS(app)
app.config['SECRET_KEY'] = 'your-super-secret-key-change-this'

SAVE_TRIP_FUNCTION_URL = "https://asia-south1-principal-lane-470311-j4.cloudfunctions.net/save-trip"
GET_TRIPS_FUNCTION_URL = "https://asia-south1-principal-lane-470311-j4.cloudfunctions.net/get-trips"
BOOK_TRIP_FUNCTION_URL = "https://asia-south1-principal-lane-470311-j4.cloudfunctions.net/book-trip"

# Initialize Firebase Admin SDK
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)

# --- Configuration ---
VERTEX_PROJECT = os.environ.get('GOOGLE_PROJECT_ID')
VERTEX_LOCATION = 'asia-south1'
if not VERTEX_PROJECT:
    raise ValueError("Missing GOOGLE_PROJECT_ID environment variable.")


# --- Define the tool for Gemini ---
def get_average_hotel_price(destination: str) -> float:
    """
    Gets the average hotel price for a destination by calling the Booking.com API.
    This is a two-step process: first get the destination ID, then search for hotels.
    """
    api_key = os.getenv('RAPIDAPI_KEY')
    if not api_key:
        print("--- ERROR: RAPIDAPI_KEY not found. Returning default price. ---")
        return 3500.0

    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "booking-com.p.rapidapi.com"
    }

    # --- Step 1: Get the Destination ID from the city name ---
    print(f"--- TOOL (Step 1): Getting Destination ID for {destination} ---")
    locations_url = "https://booking-com.p.rapidapi.com/v1/hotels/locations"
    locations_querystring = {"name": destination, "locale": "en-gb"}
    dest_id = None
    try:
        response = requests.get(locations_url, headers=headers, params=locations_querystring, timeout=10)
        response.raise_for_status()
        locations = response.json()
        for loc in locations:
            if loc.get('dest_type') == 'city':
                dest_id = loc.get('dest_id')
                break
        if not dest_id:
            print(f"--- WARN: Could not find a destination ID for {destination}. ---")
            return 3500.0
    except requests.exceptions.RequestException as e:
        print(f"--- ERROR (Step 1): API call to get destination ID failed: {e}. ---")
        return 3500.0

    # --- Step 2: Use the ID to search for hotels ---
    print(f"--- TOOL (Step 2): Searching hotels with ID {dest_id} for {destination} ---")
    search_url = "https://booking-com.p.rapidapi.com/v2/hotels/search"
    today = date.today()
    checkin_date = today + timedelta(days=60)
    checkout_date = today + timedelta(days=61)
    search_querystring = {
        "order_by": "popularity", "adults_number": "1", "units": "metric",
        "room_number": "1", "checkout_date": checkout_date.strftime("%Y-%m-%d"),
        "checkin_date": checkin_date.strftime("%Y-%m-%d"), "filter_by_currency": "INR",
        "dest_type": "city", "locale": "en-gb", "dest_id": dest_id
    }
    try:
        response = requests.get(search_url, headers=headers, params=search_querystring, timeout=20)
        response.raise_for_status()
        data = response.json()
        
        hotels = data.get('results', [])
        if not hotels:
            print(f"--- WARN: No hotels found by API for {destination}. ---")
            return 3500.0

        prices = []
        # --- THIS IS THE FINAL, CORRECTED EXTRACTION LOGIC ---
        for hotel in hotels[:5]: 
            price_breakdown = hotel.get('priceBreakdown')
            if price_breakdown:
                # Note the casing: 'grossPrice'
                gross_price_obj = price_breakdown.get('grossPrice') 
                if gross_price_obj:
                    price_value = gross_price_obj.get('value')
                    if price_value is not None:
                        prices.append(float(price_value))
        
        if not prices:
            print(f"--- WARN: Hotels found, but price values were still not extracted. Check API response structure. ---")
            return 3500.0

        average_price = sum(prices) / len(prices)
        print(f"--- TOOL RESULT: Average price for {destination} is ₹{average_price:.2f} ---")
        return average_price

    except requests.exceptions.RequestException as e:
        print(f"--- ERROR (Step 2): API call to search hotels failed: {e}. ---")
        return 3500.0

get_average_hotel_price_func = FunctionDeclaration(
    name="get_average_hotel_price",
    description="Gets the average hotel price per night for a given Indian city to help create a realistic budget.",
    parameters={
        "type": "object",
        "properties": { "destination": { "type": "string", "description": "The city in India for which to find the hotel price."} },
        "required": ["destination"]
    },
)

hotel_pricing_tool = Tool(
    function_declarations=[get_average_hotel_price_func],
)

print("--- DEBUG: hotel_pricing_tool has been DEFINED. ---")

# --- Client Initialization ---
try:
    vertexai.init(project=VERTEX_PROJECT, location=VERTEX_LOCATION)

    print("--- DEBUG: About to INITIALIZE the model... ---")
    
    # THIS IS THE CRUCIAL LINE THAT CREATES THE 'model' VARIABLE
    model = GenerativeModel("gemini-1.5-flash-002", tools=[hotel_pricing_tool])
    
    # This line initializes the Google Maps client
    gmaps = googlemaps.Client(key=os.environ.get('GOOGLE_MAPS_API_KEY'))

except Exception as e:
    # If any of the above lines fail, the app will crash on startup, which is good for debugging.
    raise RuntimeError(f"Failed to initialize clients: {e}")

# --- ROUTES ---

@app.route('/')
def index():
    """Serves the frontend HTML file from the 'templates' folder."""
    return render_template('index.html')

@app.route('/itinerary')
def show_itinerary():
    """Displays the generated itinerary from the session."""
    itinerary_data = session.get('itinerary_data', None)
    maps_api_key = os.environ.get('GOOGLE_MAPS_API_KEY')
    return render_template('itinerary.html', itinerary_data=itinerary_data, maps_api_key=maps_api_key)

@app.route('/login')
def login():
    """Renders the login page."""
    return render_template('login.html')

@app.route('/signup')  
def signup():
    """Renders the signup page."""
    return render_template('signup.html')

@app.route('/logout')
def logout():
    """Clears user session and redirects to login."""
    session.clear()
    return redirect(url_for('login'))

@app.route('/payment/<string:trip_id>')
def payment(trip_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    # You already have the logic to fetch the full trip details.
    # We are just confirming that trip_id is passed to the template.
    db = firestore.client()
    doc_ref = db.collection('trips').document(trip_id)
    doc = doc_ref.get()

    if not doc.exists or doc.to_dict().get('user_id') != session['user_id']:
        return "Trip not found or you are not authorized to view it.", 404

    trip_data = doc.to_dict()['itinerary_content']
    
    return render_template('payment.html', trip_id=trip_id, trip_data=trip_data)

@app.route('/plan', methods=['POST'])
def plan_trip():
    """Receives form data, uses tools to get real data, generates an itinerary, and redirects."""
    data = {
        "source": request.form.get('source'),
        "destination": request.form.get('destination'),
        "start_date": request.form.get('start_date'),
        "return_date": request.form.get('return_date'),
        "budget": request.form.get('budget'), # We still get it, but won't use it directly for budget
        "interests": request.form.getlist('interests'),
        "transport_mode": request.form.get('transport_mode'),
        "language": request.form.get('language'),
        "additional_reqs": request.form.get('additional_reqs')
    }

    # --- NEW PROMPT INSTRUCTING THE AI TO USE THE TOOL ---
    # --- FINAL, MORE AGGRESSIVE PROMPT ---
    prompt = f"""
    You are an expert travel agent. Your task is to create a realistic itinerary based on user input and real-world data.

    **Step 1: Get Real-World Data**
    You MUST first call the `get_average_hotel_price` tool for the user's destination: {data.get('destination')}.

    **Step 2: Adhere to the Budget**
    Once you have the real hotel price, create a complete itinerary that fits within the user's total budget of {data.get('budget')} INR. If the budget is too low for the requested duration, you MUST reduce the number of days or suggest cheaper alternatives. The 'total_estimate_inr' in your final JSON must not exceed the user's budget.

    **Step 3: Generate the Final Output**
    After all calculations are done, your entire response MUST be ONLY a single, valid JSON object. Do not add any conversational text or formatting like "```json". The JSON object MUST strictly follow this exact structure:
    {{
        "plan": [
            {{
                "day": <integer>,
                "date": "<string YYYY-MM-DD>",
                "theme": "<string>",
                "activities": [
                    {{
                        "time": "<string>",
                        "description": "<string>",
                        "location_name": "<string>",
                        "latitude": <float>,
                        "longitude": <float>
                    }}
                ]
            }}
        ],
        "cost_breakdown": {{
            "accommodation_estimate_inr": <integer>,
            "transport_estimate_inr": <integer>,
            "activities_estimate_inr": <integer>,
            "food_estimate_inr": <integer>,
            "total_estimate_inr": <integer>
        }}
    }}

    **User Request for this task:**
    - Destination: {data.get('destination')}
    - Total Budget: {data.get('budget')} INR
    - Start Date: {data.get('start_date')}
    - Return Date: {data.get('return_date')}
    - Interests: {', '.join(data.get('interests', []))}
    - Itinerary Language: {data.get('language', 'English')}
    """

    try:
        # --- NEW TOOL-USE LOGIC ---
        chat = model.start_chat()
        # Send the initial prompt to the model
        response = chat.send_message(prompt)
        
        # The model will respond with a request to call our function.
        function_call = response.candidates[0].content.parts[0].function_call
        
        if function_call and function_call.name == "get_average_hotel_price":
            # Extract the destination argument provided by the model
            destination_arg = function_call.args['destination']
            
            # Call our actual Python function to get the real price
            price_result = get_average_hotel_price(destination=destination_arg)
            
            # Send the result back to the model
            response = chat.send_message(
                Part.from_function_response(
                    name="get_average_hotel_price",
                    response={
                        "price": price_result,
                    }
                )
            )

        # The model will now use the price to generate the final itinerary.
        raw_text = response.text
        
        # --- The rest of the parsing logic is the same ---
        print("=== AI RESPONSE DEBUG (after tool use) ===")
        print("Raw response length:", len(raw_text))
        print("First 200 chars:", raw_text[:200])
        print("==========================================")
        
        cleaned_text = raw_text.strip()
        if "```json" in cleaned_text:
            cleaned_text = cleaned_text.split("```json")[1].split("```")[0]
        elif "```" in cleaned_text:
            cleaned_text = cleaned_text.split("```")[1].split("```")[0]
        
        json_start = cleaned_text.find('{')
        json_end = cleaned_text.rfind('}') + 1
        
        if json_start == -1 or json_end == 0:
            raise ValueError("No valid JSON object found in response after tool use")
            
        json_text = cleaned_text[json_start:json_end]
        ai_generated_itinerary = json.loads(json_text)
        
        final_response = {"request": data, "itinerary": ai_generated_itinerary}
        session['itinerary_data'] = final_response
        return redirect(url_for('show_itinerary'))

    except Exception as e:
        print(f"Error during trip planning with tools: {e}")
        return f"An error occurred during itinerary generation: {e}", 500

@app.route('/regenerate', methods=['POST'])
def regenerate_itinerary():
    """Receives an existing itinerary and a change request, then regenerates."""
    original_itinerary_json = request.form.get('original_itinerary')
    change_request = request.form.get('change_request')

    if not original_itinerary_json or not change_request:
        flash('Please enter your requested changes in the text box before regenerating.', 'error')
        return redirect(url_for('show_itinerary'))

    try:
        original_data = json.loads(original_itinerary_json)
        original_plan = original_data.get('itinerary', {})
        user_request = original_data.get('request', {})

        prompt = f"""
        Modify this travel itinerary based on the user's request: "{change_request}"
        
        Original itinerary: {json.dumps(original_plan, indent=2)}
        
        Return the COMPLETE modified itinerary as valid JSON with the same structure.
        IMPORTANT: Keep the same structure including latitude and longitude for each activity.
        Language: {user_request.get('language', 'English')}
        """

        response = model.generate_content(prompt)
        raw_text = response.text
        
        cleaned_text = raw_text.strip()
        if "```json" in cleaned_text:
            cleaned_text = cleaned_text.split("```json")[1].split("```")[0]
        elif "```" in cleaned_text:
            cleaned_text = cleaned_text.split("```")[1].split("```")[0]
        
        json_start = cleaned_text.find('{')
        json_end = cleaned_text.rfind('}') + 1
        json_text = cleaned_text[json_start:json_end]
        
        ai_generated_itinerary = json.loads(json_text)
        final_response = {"request": user_request, "itinerary": ai_generated_itinerary}
        session['itinerary_data'] = final_response

        return redirect(url_for('show_itinerary'))

    except Exception as e:
        print(f"Regeneration error: {e}")
        flash(f'Error regenerating itinerary: {str(e)}', 'error')
        return redirect(url_for('show_itinerary'))

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

@app.route('/confirm-booking', methods=['POST'])
def confirm_booking():
    """
    This single route handles the entire booking confirmation process.
    1. Calls the Cloud Function to update the trip status.
    2. Creates the session object for the confirmation page with the correct total.
    3. Redirects to the confirmation page.
    """
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "User not logged in."}), 401

    try:
        data = request.get_json()
        trip_id = data.get('trip_id')
        if not trip_id:
            return jsonify({"status": "error", "message": "Missing trip_id"}), 400

        # --- Part 1: Call the Cloud Function to book the trip ---
        auth_header = request.headers.get('Authorization')
        proxy_headers = {'Authorization': auth_header, 'Content-Type': 'application/json'}
        proxy_response = requests.post(BOOK_TRIP_FUNCTION_URL, json={"trip_id": trip_id}, headers=proxy_headers, timeout=20)
        proxy_response.raise_for_status() # This will raise an error if the cloud function fails

        # --- Part 2: Create the confirmation object for the session ---
        db = firestore.client()
        doc_ref = db.collection('trips').document(trip_id)
        doc = doc_ref.get()
        if not doc.exists:
            return jsonify({"status": "error", "message": "Trip not found after booking"}), 404

        trip_data = doc.to_dict()['itinerary_content']
        total_amount = trip_data.get('itinerary', {}).get('cost_breakdown', {}).get('total_estimate_inr', 0)
        
        import random
        booking_id = f"ATP-{random.randint(100000, 999999)}"
        
        booking_confirmation = {
            "booking_id": booking_id,
            "status": "confirmed",
            "trip_data": trip_data,
            "payment_method": "Credit Card",
            "booking_date": date.today().strftime("%Y-%m-%d"),
            "total_amount": total_amount
        }
        
        session['booking_confirmation'] = booking_confirmation
        
        # --- Part 3: Respond to the client ---
        # Tell the JavaScript that it was successful and where to redirect.
        return jsonify({"status": "success", "redirect_url": url_for('booking_confirmation')})

    except Exception as e:
        print(f"--- FATAL ERROR in confirm_booking: {e} ---")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/booking-confirmation')
def booking_confirmation():
    """Displays the NEW booking confirmation page."""
    confirmation_data = session.get('booking_confirmation', None)
    if not confirmation_data:
        flash('No booking confirmation found.', 'error')
        return redirect(url_for('index'))
    return render_template('booking_success.html', confirmation=confirmation_data)

@app.route('/dashboard')
def dashboard():
    # Check if a user_id is in the session. This proves they are logged in.
    if 'user_id' in session:
        # The user is authenticated. Render the dashboard page.
        # We can now use session['user_id'] to fetch their specific data.
        # For example: user = auth.get_user(session['user_id'])
        return render_template('dashboard.html')
    else:
        # The user is not logged in. Redirect them to the login page.
        return redirect(url_for('login'))

@app.route('/sessionLogin', methods=['POST'])
def session_login():
    try:
        # Get the ID token sent from the client
        id_token = request.json['idToken']

        # Verify the ID token with Firebase Admin SDK
        decoded_token = auth.verify_id_token(id_token)

        # The token is valid. Get the user's unique ID (uid) from it.
        uid = decoded_token['uid']
        
        # Store the user's uid in the server-side session.
        # This is our way of "logging in" the user on the backend.
        session['user_id'] = uid
        
        return jsonify({"status": "success"})

    except Exception as e:
        # If the token is invalid or expired, an error will be thrown.
        return jsonify({"status": "error", "message": str(e)}), 401

@app.route('/save-trip-proxy', methods=['POST'])
def save_trip_proxy():
    # 1. Security check: Ensure user is logged into Flask session
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    try:
        # 2. Get the ID token and data from the client request
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({"status": "error", "message": "Missing Authorization header"}), 400

        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "Missing JSON payload"}), 400

        # 3. Forward the request to the Google Cloud Function
        # The Cloud Function will do its own token verification
        headers = {'Authorization': auth_header, 'Content-Type': 'application/json'}
        
        # Make the server-to-server request
        response = requests.post(SAVE_TRIP_FUNCTION_URL, json=data, headers=headers, timeout=15)
        
        # 4. Check the response from the Cloud Function and relay it to the client
        if response.status_code == 200:
            return jsonify({"status": "success", "data": response.json()}), 200
        else:
            # Relay the error from the Cloud Function
            return jsonify({
                "status": "error", 
                "message": f"Cloud Function failed with status {response.status_code}: {response.text}"
            }), response.status_code

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get-user-trips-proxy', methods=['GET'])
def get_user_trips_proxy():
    # 1. Security check: Ensure user is logged into Flask session
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    try:
        # 2. Get the ID token from the client request's Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({"status": "error", "message": "Missing Authorization header"}), 400

        # 3. Forward the request to the Google Cloud Function
        # The function needs the user's token to know whose trips to fetch
        headers = {'Authorization': auth_header, 'Content-Type': 'application/json'}
        
        # Make the server-to-server GET request to our new function
        response = requests.get(GET_TRIPS_FUNCTION_URL, headers=headers, timeout=20)
        
        # 4. Check the response and relay it back to the client
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        
        return jsonify(response.json()), 200

    except requests.exceptions.HTTPError as e:
        # Relay the specific error from the Cloud Function
        return jsonify({
            "status": "error", 
            "message": f"Cloud Function failed with status {e.response.status_code}: {e.response.text}"
        }), e.response.status_code
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/trip/<string:trip_id>')
def trip_details(trip_id):
    # 1. Security: Check if user is logged in
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        # 2. Fetch the specific trip document from Firestore using its ID
        db = firestore.client()
        doc_ref = db.collection('trips').document(trip_id)
        doc = doc_ref.get()

        if not doc.exists:
            # If no trip with that ID exists, show a 404 Not Found error
            return "Trip not found.", 404

        trip_data = doc.to_dict()

        # 3. Authorization: Check if the logged-in user owns this trip
        if trip_data.get('user_id') != session['user_id']:
            # If they don't own it, deny access
            return "You are not authorized to view this trip.", 403

        # 4. **THE FIX IS HERE**
        # The data is already a dictionary (map) in Firestore, so we don't need json.loads.
        full_itinerary_data = trip_data['itinerary_content']
        
        # 5. Render a new template, passing the full itinerary data to it
        return render_template('trip_details.html', itinerary_data=full_itinerary_data)

    except Exception as e:
        # Handle any other errors gracefully
        return f"An error occurred: {e}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)), debug=True)