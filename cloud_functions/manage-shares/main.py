import functions_framework
import firebase_admin
from firebase_admin import firestore

try:
    firebase_admin.initialize_app()
except ValueError:
    pass

@functions_framework.http
def manage_trip_shares(request):
    """Manage trip sharing analytics and cleanup."""
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Authorization, Content-Type',
    }
    
    if request.method == 'OPTIONS':
        return ('', 204, headers)
    
    try:
        db = firestore.client()
        
        if request.method == 'GET':
            # Get sharing analytics for a user
            shares = db.collection('shared_trips').where('created_by', '==', user_id).stream()
            analytics = []
            for share in shares:
                share_data = share.to_dict()
                analytics.append({
                    'share_id': share.id,
                    'view_count': share_data.get('view_count', 0),
                    'created_at': share_data.get('created_at')
                })
            return (analytics, 200, headers)
            
        elif request.method == 'DELETE':
            # Delete a shared trip
            share_id = request.json.get('share_id')
            db.collection('shared_trips').document(share_id).delete()
            return ({'status': 'deleted'}, 200, headers)
            
    except Exception as e:
        return (f'Error: {str(e)}', 500, headers)