import os
from dotenv import load_dotenv
import json
import vertexai
from flask import Flask, request, jsonify, render_template, session, redirect, url_for, flash, send_file
from flask_cors import CORS
from vertexai.generative_models import GenerativeModel, Tool, FunctionDeclaration, Part
import googlemaps
import firebase_admin
from firebase_admin import credentials, auth, firestore
import requests
from datetime import datetime, date, timedelta
import uuid
import qrcode
import io
import base64
from urllib.parse import quote
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import time
from google.api_core.exceptions import ResourceExhausted



load_dotenv()

# --- Initialization ---
app = Flask(__name__, template_folder='templates')

# Security: Use environment variable for secret key with fallback
SECRET_KEY = os.environ.get('FLASK_SECRET_KEY')
if not SECRET_KEY:
    if os.environ.get('FLASK_ENV') == 'production':
        raise ValueError("FLASK_SECRET_KEY environment variable must be set in production")
    # Only use fallback in development
    SECRET_KEY = 'dev-secret-key-change-in-production'
    print("WARNING: Using development secret key. Set FLASK_SECRET_KEY in production!")

app.secret_key = SECRET_KEY
app.config['SECRET_KEY'] = SECRET_KEY
CORS(app)

SAVE_TRIP_FUNCTION_URL = "https://asia-south1-principal-lane-470311-j4.cloudfunctions.net/save-trip"
GET_TRIPS_FUNCTION_URL = "https://asia-south1-principal-lane-470311-j4.cloudfunctions.net/get-trips"
BOOK_TRIP_FUNCTION_URL = "https://asia-south1-principal-lane-470311-j4.cloudfunctions.net/book-trip"
MANAGE_SHARES_FUNCTION_URL = "https://asia-south1-principal-lane-470311-j4.cloudfunctions.net/manage-trip-shares"

# Initialize Firebase Admin SDK
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)



# --- Configuration ---
VERTEX_PROJECT = os.environ.get('GOOGLE_PROJECT_ID')
VERTEX_LOCATION = 'asia-south1'

# Validate required environment variables
required_env_vars = {
    'GOOGLE_PROJECT_ID': VERTEX_PROJECT,
    'GOOGLE_MAPS_API_KEY': os.environ.get('GOOGLE_MAPS_API_KEY')
}

missing_vars = [var for var, value in required_env_vars.items() if not value]
if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

# Optional environment variables with warnings
optional_env_vars = {
    'RAPIDAPI_KEY': 'Hotel pricing will use default values',
    'OPENWEATHER_API_KEY': 'Weather features will be disabled'
}

for var, warning in optional_env_vars.items():
    if not os.environ.get(var):
        print(f"WARNING: {var} not set. {warning}")


# --- Define the tool for Gemini ---
def get_average_hotel_price(destination: str) -> float:
    """
    Gets the average hotel price for a destination by calling the Booking.com API.
    This is a two-step process: first get the destination ID, then search for hotels.
    
    Args:
        destination (str): The city name to search for
        
    Returns:
        float: Average hotel price in INR, defaults to 3500.0 if API fails
    """
    api_key = os.getenv('RAPIDAPI_KEY')
    if not api_key:
        print("INFO: RAPIDAPI_KEY not found. Using default hotel price.")
        return 3500.0

    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "booking-com.p.rapidapi.com"
    }
    

    # --- Step 1: Get the Destination ID from the city name ---
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
            print(f"WARNING: Could not find destination ID for {destination}")
            return 3500.0
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to get destination ID: {e}")
        return 3500.0

    # --- Step 2: Use the ID to search for hotels ---
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
            print(f"WARNING: No hotels found for {destination}")
            return 3500.0

        prices = []
        # Extract hotel prices from API response
        for hotel in hotels[:5]: 
            price_breakdown = hotel.get('priceBreakdown')
            if price_breakdown:
                gross_price_obj = price_breakdown.get('grossPrice') 
                if gross_price_obj:
                    price_value = gross_price_obj.get('value')
                    if price_value is not None:
                        prices.append(float(price_value))
        
        if not prices:
            print(f"WARNING: Could not extract prices for {destination}")
            return 3500.0

        average_price = sum(prices) / len(prices)
        print(f"INFO: Average hotel price for {destination}: ₹{average_price:.2f}")
        return average_price

    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to search hotels: {e}")
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


weather_tool_func = FunctionDeclaration(
    name="get_todays_weather",
    description="Gets the current weather forecast for a specific city in India. Use this to make real-time adjustments to a travel plan.",
    parameters={
        "type": "object",
        "properties": { "destination": { "type": "string", "description": "The city name, e.g., 'Mumbai'."} },
        "required": ["destination"]
    },
)

combined_tool = Tool(
    function_declarations=[
        get_average_hotel_price_func, 
        weather_tool_func
    ],
)

# --- Client Initialization ---
try:
    vertexai.init(project=VERTEX_PROJECT, location=VERTEX_LOCATION)
    
    # Initialize the Gemini model with tools
    model = GenerativeModel("gemini-2.5-flash", tools=[combined_tool])
    
    # Initialize Google Maps client
    gmaps = googlemaps.Client(key=os.environ.get('GOOGLE_MAPS_API_KEY'))
    
    print("INFO: Successfully initialized Vertex AI and Google Maps clients")

except Exception as e:
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
    You are an expert travel agent. Create a realistic itinerary based on user input and real-world data.

    **IMPORTANT: Do NOT include any Python code in your response. Your response MUST be ONLY a valid JSON object.**

    **Step 1: Get Real-World Data**
    You MUST first call the `get_average_hotel_price` tool for the user's destination: {data.get('destination')}.

    **Step 2: Adhere to the Budget**
    Once you have the real hotel price, create a complete itinerary that fits within the user's total budget of {data.get('budget')} INR. If the budget is too low for the requested duration, you MUST reduce the number of days or suggest cheaper alternatives. The 'total_estimate_inr' in your final JSON must not exceed the user's budget.

    **Step 3: Generate the Final Output**
    After all calculations are done, your entire response MUST be ONLY a single, valid JSON object. Do not add any conversational text or formatting like "```json". The JSON object MUST strictly follow this exact structure:
    ***CRITICAL LANGUAGE INSTRUCTION: All text values within the JSON, such as 'theme' and 'description', MUST be written in the following language: {data.get('language', 'English')}.***

    The JSON object MUST strictly follow this exact structure:
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

    # --- Start of new structure ---
    # --- This is the new, corrected structure ---

    # --- This is the new, more robust multi-tool handling loop ---

    # --- This is the final, corrected structure for the plan_trip function ---

    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Initialize chat session
            chat = model.start_chat(response_validation=False)
            response = chat.send_message(prompt)

            # Handle function calls from AI with safety limit
            tool_call_count = 0
            max_tool_calls = 5  # Prevent infinite loops
            
            while tool_call_count < max_tool_calls:
                part = response.candidates[0].content.parts[0]
                function_call = getattr(part, 'function_call', None)

                if not function_call:
                    break # Exit loop if AI is done calling tools

                tool_call_count += 1

                if function_call.name == "get_average_hotel_price":
                    price_result = get_average_hotel_price(destination=function_call.args['destination'])
                    response = chat.send_message(Part.from_function_response(name="get_average_hotel_price", response={"price": price_result}))

                elif function_call.name == "get_todays_weather":
                    weather_result = get_todays_weather(destination=function_call.args['destination'])
                    response = chat.send_message(Part.from_function_response(name="get_todays_weather", response=weather_result))
                
                else:
                    print(f"WARNING: Unknown function call: {function_call.name}")
                    break # Unknown tool, exit loop
            
            if tool_call_count >= max_tool_calls:
                print("WARNING: Maximum tool calls reached, proceeding with current response")
            
            # Parse AI response
            raw_text = response.text
            
            cleaned_text = raw_text.strip()
            if "```json" in cleaned_text:
                cleaned_text = cleaned_text.split("```json")[1].split("```")[0]
            elif "```" in cleaned_text:
                cleaned_text = cleaned_text.split("```")[1].split("```")[0]
            
            json_start = cleaned_text.find('{')
            json_end = cleaned_text.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("No valid JSON object found in AI response")
                
            json_text = cleaned_text[json_start:json_end]
            ai_generated_itinerary = json.loads(json_text)
            
            final_response = {"request": data, "itinerary": ai_generated_itinerary}
            session['itinerary_data'] = final_response

            # If we get here, everything worked. Redirect and exit the function.
            return redirect(url_for('show_itinerary'))

        except ResourceExhausted as e:
            print(f"Attempt {attempt + 1} failed: Rate limit exceeded. Retrying...")
            if attempt + 1 == max_retries:
                flash("Our AI service is currently busy. Please try again in a few minutes.", "error")
                return redirect(url_for('index'))
            time.sleep(2)
        
        except Exception as e:
            error_message = str(e)
            print(f"Trip planning error: {error_message}")
            
            if "Malformed function call" in error_message:
                flash("Unable to create itinerary with current parameters. Please try different dates or destination.", "error")
                return redirect(url_for('index'))
            elif "Resource Exhausted" in error_message or "429" in error_message:
                flash("Our AI service is currently busy. Please try again in a few minutes.", "error")
                return redirect(url_for('index'))
            else:
                flash("An error occurred while creating your itinerary. Please try again.", "error")
                return redirect(url_for('index'))

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
        today_date = date.today().strftime("%Y-%m-%d")
        # 5. Render a new template, passing the full itinerary data to it
        return render_template('trip_details.html', itinerary_data=full_itinerary_data,today_date=today_date,maps_api_key=os.environ.get('GOOGLE_MAPS_API_KEY'))

    except Exception as e:
        # Handle any other errors gracefully
        return f"An error occurred: {e}", 500

@app.route('/share-trip/<trip_id>')
def make_trip_shareable(trip_id):
    """Generate a public shareable link for a trip."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        # Verify user owns this trip
        db = firestore.client()
        trip_ref = db.collection('trips').document(trip_id)
        trip_doc = trip_ref.get()
        
        if not trip_doc.exists or trip_doc.to_dict().get('user_id') != session['user_id']:
            return "Unauthorized", 403
            
        # Generate unique share ID
        share_id = str(uuid.uuid4())
        
        # Create shareable version
        share_data = {
            'original_trip_id': trip_id,
            'share_id': share_id,
            'created_by': session['user_id'],
            'created_at': firestore.SERVER_TIMESTAMP,
            'is_public': True,
            'view_count': 0
        }
        
        db.collection('shared_trips').document(share_id).set(share_data)
        
        # Generate shareable URL
        share_url = request.host_url + f'shared/{share_id}'
        
        return render_template('share_success.html', 
                             share_url=share_url, 
                             trip_id=trip_id,
                             qr_code=generate_qr_code(share_url))
        
    except Exception as e:
        return f"Error creating shareable link: {str(e)}", 500

@app.route('/shared/<share_id>')
def view_shared_trip(share_id):
    """Public view of shared trip - no authentication required."""
    try:
        db = firestore.client()
        
        # Get share data
        share_ref = db.collection('shared_trips').document(share_id)
        share_doc = share_ref.get()
        
        if not share_doc.exists:
            return render_template('share_not_found.html'), 404
            
        share_data = share_doc.to_dict()
        
        # Increment view count
        share_ref.update({'view_count': firestore.Increment(1)})
        
        # Get original trip data
        trip_ref = db.collection('trips').document(share_data['original_trip_id'])
        trip_doc = trip_ref.get()
        
        if not trip_doc.exists:
            return render_template('share_not_found.html'), 404
            
        trip_data = trip_doc.to_dict()
        itinerary_data = trip_data['itinerary_content']
        
        # Get creator info (optional - for attribution)
        creator_info = get_user_display_name(share_data['created_by'])
        
        return render_template('shared_trip.html', 
                             itinerary_data=itinerary_data,
                             share_data=share_data,
                             creator_info=creator_info,
                             maps_api_key=os.environ.get('GOOGLE_MAPS_API_KEY'))
        
    except Exception as e:
        return f"Error loading shared trip: {str(e)}", 500

@app.route('/export-pdf/<trip_id>')
def export_trip_pdf(trip_id):
    """Export trip as PDF."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        # Get trip data (verify ownership)
        db = firestore.client()
        trip_ref = db.collection('trips').document(trip_id)
        trip_doc = trip_ref.get()
        
        if not trip_doc.exists or trip_doc.to_dict().get('user_id') != session['user_id']:
            return "Unauthorized", 403
            
        trip_data = trip_doc.to_dict()
        itinerary_data = trip_data['itinerary_content']
        
        # Generate PDF
        pdf_buffer = generate_trip_pdf(itinerary_data)
        
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=f"trip-{itinerary_data['request']['destination']}.pdf",
            mimetype='application/pdf'
        )
        
    except Exception as e:
        return f"Error generating PDF: {str(e)}", 500

# Helper functions
def generate_qr_code(url):
    """Generate QR code for sharing URL."""
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    # Convert to base64 for embedding in HTML
    qr_code_data = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/png;base64,{qr_code_data}"

def get_user_display_name(user_id):
    """Get user display name for attribution."""
    try:
        user = auth.get_user(user_id)
        return user.display_name or user.email.split('@')[0]
    except:
        return "Anonymous Traveler"

def generate_trip_pdf(itinerary_data):
    """Generates a complete, multi-page PDF from the itinerary data."""
    
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter # Get page dimensions

    # --- Reusable Drawing Functions ---
    def check_page_break(y_pos, needed_space=50):
        """Creates a new page if there isn't enough space."""
        if y_pos < needed_space:
            p.showPage()
            p.setFont("Helvetica", 9)
            p.drawString(width - inch, 0.5 * inch, f"Page {p.getPageNumber()}")
            return height - inch # Return new y_pos at the top
        return y_pos

    def draw_wrapped_text(text, x, y, max_width, font_name="Helvetica", font_size=10):
        """Draws text that wraps automatically."""
        p.setFont(font_name, font_size)
        lines = []
        # Basic word wrapping
        for line in text.split('\n'):
            words = line.split()
            while len(words) > 0:
                line_text = ""
                while len(words) > 0 and p.stringWidth(line_text + words[0], font_name, font_size) < max_width:
                    line_text += words.pop(0) + " "
                lines.append(line_text)
        
        for line in lines:
            p.drawString(x, y, line)
            y -= font_size * 1.2
        return y


    # --- Start PDF Generation ---
    y = height - inch # Start y-position
    
    # 1. Header Section
    p.setFont("Helvetica-Bold", 24)
    p.setFillColor(colors.HexColor('#2d6cdf'))
    p.drawString(inch, y, f"Your Trip to {itinerary_data['request']['destination']}")
    y -= 30
    
    p.setFont("Helvetica", 12)
    p.setFillColor(colors.black)
    p.drawString(inch, y, f"From: {itinerary_data['request']['source']}")
    y -= 20
    p.drawString(inch, y, f"Dates: {itinerary_data['request']['start_date']} to {itinerary_data['request']['return_date']}")
    y -= 30
    p.line(inch, y, width - inch, y) # Horizontal line
    y -= 30
    
    # 2. Daily Plan Section
    for day in itinerary_data['itinerary']['plan']:
        y = check_page_break(y, needed_space=150) # Check if space for day header + 1 activity
        
        p.setFont("Helvetica-Bold", 16)
        p.setFillColor(colors.HexColor('#1b4fa0'))
        p.drawString(inch, y, f"Day {day['day']}: {day['theme']} ({day['date']})")
        y -= 25

        for activity in day['activities']:
            y = check_page_break(y)
            p.setFont("Helvetica-Bold", 11)
            p.setFillColor(colors.black)
            p.drawString(inch + 0.2*inch, y, f"{activity['time']}:")
            
            # Use wrapped text for description
            y = draw_wrapped_text(f"{activity['description']} ({activity['location_name']})", 
                                  inch + 1.2*inch, y, max_width=width - 2.5*inch)
            y -= 10 # Extra space after each activity
    
        y -= 20 # Extra space after each day
    
    # 3. Cost Breakdown Section
    y = check_page_break(y, needed_space=180)
    p.line(inch, y, width - inch, y)
    y -= 30
    
    p.setFont("Helvetica-Bold", 18)
    p.setFillColor(colors.HexColor('#2d6cdf'))
    p.drawString(inch, y, "Estimated Cost Breakdown")
    y -= 30
    
    costs = itinerary_data['itinerary']['cost_breakdown']
    p.setFont("Helvetica", 12)
    p.setFillColor(colors.black)
    
    cost_items = [
        ("Accommodation:", costs.get("accommodation_estimate_inr", 0)),
        ("Transport:", costs.get("transport_estimate_inr", 0)),
        ("Activities:", costs.get("activities_estimate_inr", 0)),
        ("Food:", costs.get("food_estimate_inr", 0)),
    ]
    
    for label, value in cost_items:
        p.drawString(inch, y, label)
        p.drawRightString(width - inch, y, f"₹{value:,}")
        y -= 20

    y -= 10
    p.line(inch, y, width - inch, y)
    y -= 20
    
    p.setFont("Helvetica-Bold", 14)
    p.drawString(inch, y, "Total Estimated Cost:")
    p.drawRightString(width - inch, y, f"₹{costs.get('total_estimate_inr', 0):,}")
    
    # --- Finalize PDF ---
    p.save()
    buffer.seek(0)
    return buffer

@app.route('/get-share-analytics-proxy', methods=['GET'])
def get_share_analytics_proxy():
    """
    Proxy route to get share analytics (view counts, etc.) for the logged-in user.
    """
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({"status": "error", "message": "Missing Authorization header"}), 400

        headers = {'Authorization': auth_header}
        
        # Use the NEW constant to call the manage-shares function with a GET request
        response = requests.get(MANAGE_SHARES_FUNCTION_URL, headers=headers, timeout=20)
        
        response.raise_for_status() # Raise an error if the function fails
        
        return jsonify(response.json()), 200

    except Exception as e:
        return jsonify({"status": "error", "message": f"Error fetching share analytics: {str(e)}"}), 500


@app.route('/delete-share-link-proxy', methods=['POST'])
def delete_share_link_proxy():
    """
    Proxy route to delete a specific public share link.
    """
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    
    try:
        auth_header = request.headers.get('Authorization')
        data = request.get_json()
        share_id = data.get('share_id')

        if not all([auth_header, share_id]):
            return jsonify({"status": "error", "message": "Missing authorization or share_id"}), 400

        headers = {'Authorization': auth_header, 'Content-Type': 'application/json'}
        
        # Use the NEW constant to call the manage-shares function with a DELETE request
        # Note: We use requests.delete() to match the method the Cloud Function expects
        response = requests.delete(MANAGE_SHARES_FUNCTION_URL, json={"share_id": share_id}, headers=headers, timeout=15)
        
        response.raise_for_status()
        
        return jsonify(response.json()), 200

    except Exception as e:
        return jsonify({"status": "error", "message": f"Error deleting share link: {str(e)}"}), 500

# ADD THIS NEW, CORRECTED FUNCTION IN ITS PLACE
def get_todays_weather(destination: str) -> dict:
    """
    Gets the current weather forecast for a specific city using the OpenWeatherMap API.
    
    Args:
        destination (str): The city name to get weather for
        
    Returns:
        dict: Weather information or error message
    """
    api_key = os.getenv('OPENWEATHER_API_KEY')
    if not api_key:
        print("WARNING: OPENWEATHER_API_KEY not found. Weather features disabled.")
        return {"error": "Weather service is not configured."}
    
    # Construct the API URL
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": destination,
        "appid": api_key,
        "units": "metric"  # For temperature in Celsius
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status() # Raise an error for bad status codes
        data = response.json()

        # Parse the response from OpenWeatherMap
        condition = data.get('weather', [{}])[0].get('main', 'Unknown')
        description = data.get('weather', [{}])[0].get('description', 'No description')
        temp_celsius = data.get('main', {}).get('temp', 0)

        weather_report = {
            "condition": condition,
            "description": f"Current condition is {description}",
            "temperature_celsius": temp_celsius
        }
        
        print(f"INFO: Weather for {destination}: {weather_report}")
        return weather_report
        
    except requests.exceptions.HTTPError as e:
        print(f"ERROR: Weather API HTTP Error: {e.response.status_code}")
        return {"error": f"Could not retrieve weather: {e.response.status_code}"}
    except Exception as e:
        print(f"ERROR: Weather API Error: {e}")
        return {"error": f"Could not retrieve weather: {e}"}


@app.route('/adjust-for-weather', methods=['POST'])
def adjust_for_weather():
    """
    Receives a day's plan and adjusts it based on real-time weather.
    """
    data = request.get_json()
    original_activities = data.get('activities')
    destination = data.get('destination')

    # This prompt instructs the AI to use the weather tool and modify the plan
    prompt = f"""
    You are a smart travel assistant. Your task is to adjust a user's plan for today based on the current weather.

    1.  **MUST call the `get_todays_weather` tool for the destination: {destination}.**
    2.  Based on the weather condition (e.g., "Rain", "Clear", "Clouds") and temperature, review the following list of activities.
    3.  If the weather is bad (e.g., "Rain", "Thunderstorm", "Extreme heat over 35°C"), you MUST replace outdoor activities with suitable indoor alternatives (e.g., museums, indoor markets, cinemas, malls, art galleries).
    4.  If the weather is good, you can keep the existing activities or suggest even better outdoor options.
    5.  Your final output MUST be only a valid JSON array of the adjusted activities, keeping the original structure. Do not add any conversational text.

    Original activities for today:
    {json.dumps(original_activities, indent=2)}
    """

    # Inside the adjust_for_weather function

    # Find the try...except block in your adjust_for_weather function and replace it with this:
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Initialize chat session
            chat = model.start_chat(response_validation=False)
            response = chat.send_message(prompt)
            
            # Handle function calls from AI with safety limit
            tool_call_count = 0
            max_tool_calls = 5  # Prevent infinite loops
            
            while tool_call_count < max_tool_calls:
                part = response.candidates[0].content.parts[0]
                function_call = getattr(part, 'function_call', None)
                if not function_call:
                    break

                tool_call_count += 1

                if function_call.name == "get_todays_weather":
                    weather_result = get_todays_weather(destination=destination)
                    response = chat.send_message(
                        Part.from_function_response(name="get_todays_weather", response=weather_result)
                    )
                else:
                    print(f"WARNING: Unknown function call: {function_call.name}")
                    break
            
            if tool_call_count >= max_tool_calls:
                print("WARNING: Maximum tool calls reached")
            
            # Parse AI response
            raw_text = response.text.strip()
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0]
            
            json_start = raw_text.find('[')
            json_end = raw_text.rfind(']') + 1
            json_text = raw_text[json_start:json_end]

            adjusted_activities = json.loads(json_text)
            
            return jsonify(adjusted_activities)

        except ResourceExhausted as e:
            # This handles the 429 error and tells the loop to retry
            print(f"--- Weather Adjust Attempt {attempt + 1} failed: Resource Exhausted. Retrying... ---")
            if attempt + 1 == max_retries:
                return jsonify({"error": "AI service is busy (429). Please try again."}), 503
            time.sleep(2)

        except Exception as e:
            # This handles any other error
            print(f"Error during weather adjustment: {e}")
            if attempt + 1 == max_retries:
                return jsonify({"error": str(e)}), 500
            time.sleep(1)


if __name__ == "__main__":
    app.run(
        debug=False,
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 8080))
    )