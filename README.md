
# AI Trip Planner

An AI-powered personalized trip planner for India, leveraging Google Vertex AI, Gemini, Maps API, Firebase, and BigQuery. It dynamically creates end-to-end itineraries tailored to individual budgets, interests, and real-time conditions, with seamless booking and payment capabilities.

## Features
- Dynamic itinerary generation (budget, duration, interests)
- Aggregates data from maps, events, local guides
- Multilingual, interactive interface (language selection)
- Real-time smart adjustments (weather, delays, last-minute bookings)
- Shareable, optimized itinerary with cost breakdown
- One-click booking and payment
- Modern, user-friendly frontend UI

## Tech Stack
- Python 3.13+
- Flask (backend API)
- Google Vertex AI, Gemini
- Google Maps API
- Firebase
- BigQuery
- HTML/CSS/JavaScript (frontend)

## Backend Endpoints
- `POST /plan`: Generate itinerary based on user preferences (budget, duration, interests, location, language). Returns itinerary, cost breakdown, and shareable link.
- `POST /book`: Book the generated itinerary (mock integration, returns confirmation).
- `POST /adjust`: Request real-time itinerary adjustments (mock integration, returns updated itinerary).

## Frontend
- Located in `frontend/index.html`
- Modern UI for entering trip details, viewing itinerary, booking, and requesting adjustments

## Getting Started
1. Ensure Python 3.13+ is installed.
2. Set up Google Cloud APIs and credentials (Vertex AI, Maps, etc.).
3. Install dependencies:
   ```sh
   pip install flask google-cloud-vertex-ai googlemaps firebase-admin google-cloud-bigquery
   ```
4. Run the backend server:
   ```sh
   python main.py
   ```
5. Open `frontend/index.html` in your browser.

## Project Structure
- `main.py`: Backend server and API endpoints
- `requirements.txt`: Python dependencies
- `frontend/index.html`: Web interface for trip planning

## Notes
- Replace placeholder API keys and credentials with your own for production use.
- The booking and adjustment features are currently mock implementations.

---
