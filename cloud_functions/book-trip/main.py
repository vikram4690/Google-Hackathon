import functions_framework
import firebase_admin
from firebase_admin import auth, firestore

try:
    firebase_admin.initialize_app()
except ValueError:
    pass

@functions_framework.http
def book_trip_status(request):
    """
    HTTP Cloud Function to update a trip's status to 'booked'.
    Expects a POST request with JSON: {"trip_id": "someId"}
    """
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Authorization, Content-Type',
    }
    if request.method == 'OPTIONS':
        return ('', 204, headers)

    # --- Authentication ---
    try:
        auth_header = request.headers.get('Authorization')
        id_token = auth_header.split('Bearer ')[1]
        decoded_token = auth.verify_id_token(id_token)
        user_id = decoded_token['uid']
    except Exception as e:
        return (f'Unauthorized: {str(e)}', 401, headers)

    # --- Data Processing ---
    try:
        request_json = request.get_json(silent=True)
        trip_id = request_json.get('trip_id')
        if not trip_id:
            return ('Bad Request: Missing trip_id', 400, headers)

        db = firestore.client()
        doc_ref = db.collection('trips').document(trip_id)
        doc = doc_ref.get()

        if not doc.exists:
            return ('Not Found: Trip does not exist', 404, headers)
        
        # Authorization: Ensure the user owns the trip they are trying to book
        trip_data = doc.to_dict()
        if trip_data.get('user_id') != user_id:
            return ('Forbidden: You are not authorized to book this trip', 403, headers)
        
        # Update the document
        doc_ref.update({'status': 'booked'})

        return ({'status': 'success', 'message': f'Trip {trip_id} booked successfully.'}, 200, headers)
    except Exception as e:
        return (f'Internal Server Error: {str(e)}', 500, headers)