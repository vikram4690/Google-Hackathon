import functions_framework
import firebase_admin
from firebase_admin import credentials, auth, firestore

# Initialize Firebase Admin SDK.
# This happens once when the function instance is created.
try:
    firebase_admin.initialize_app()
except ValueError:
    # This prevents re-initialization if the function is warm-started
    pass

@functions_framework.http
def save_trip_to_firestore(request):
    """
    HTTP Cloud Function to save a trip itinerary to Firestore.
    Expects a POST request with JSON data.
    """
    # Set CORS headers for preflight requests and the main request.
    # This allows your web app (from a different origin) to call this function.
    headers = {
        'Access-Control-Allow-Origin': '*', # Or specify your app's domain for better security
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Authorization, Content-Type',
    }

    if request.method == 'OPTIONS':
        return ('', 204, headers)

    # --- Authentication ---
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return ('Unauthorized: Missing or invalid Authorization header', 401, headers)
        
        id_token = auth_header.split('Bearer ')[1]
        decoded_token = auth.verify_id_token(id_token)
        user_id = decoded_token['uid']

    except Exception as e:
        return (f'Unauthorized: {str(e)}', 401, headers)

    # --- Data Processing ---
    try:
        request_json = request.get_json(silent=True)
        if not request_json:
            return ('Bad Request: No JSON payload found', 400, headers)

        source = request_json.get('source')
        destination = request_json.get('destination')
        itinerary = request_json.get('itinerary_content')

        if not all([source, destination, itinerary]):
            return ('Bad Request: Missing required trip data fields', 400, headers)

        # Get a client to the Firestore database
        db = firestore.client()
        
        trip_data = {
            'user_id': user_id,
            'source': source,
            'destination': destination,
            'itinerary_content': itinerary,
            'created_at': firestore.SERVER_TIMESTAMP # Use server time
        }
        
        # Add the data to a 'trips' collection in Firestore
        update_time, doc_ref = db.collection('trips').add(trip_data)

        return ({'status': 'success', 'trip_id': doc_ref.id}, 200, headers)

    except Exception as e:
        return (f'Internal Server Error: {str(e)}', 500, headers)