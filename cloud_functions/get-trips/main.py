import functions_framework
import firebase_admin
from firebase_admin import auth, firestore

# Initialize Firebase Admin SDK
try:
    firebase_admin.initialize_app()
except ValueError:
    pass

@functions_framework.http
def get_user_trips(request):
    """
    HTTP Cloud Function to fetch all trips for an authenticated user.
    Expects a GET request with an Authorization header.
    """
    # Set CORS headers
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
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

    # --- Data Fetching ---
    try:
        db = firestore.client()
        
        # Query the 'trips' collection for documents where 'user_id' matches
        trips_query = db.collection('trips').where('user_id', '==', user_id).order_by('created_at', direction=firestore.Query.DESCENDING)
        
        results = trips_query.stream()
        
        # Format the documents into a list of dictionaries
        trips_list = []
        for trip in results:
            trip_data = trip.to_dict()
            trip_data['id'] = trip.id # Add the document ID to the data
            
            # Convert datetime object to a string so it can be sent as JSON
            if 'created_at' in trip_data and hasattr(trip_data['created_at'], 'isoformat'):
                trip_data['created_at'] = trip_data['created_at'].isoformat()
            
            trips_list.append(trip_data)

        return (trips_list, 200, headers)

    except Exception as e:
        return (f'Internal Server Error: {str(e)}', 500, headers)