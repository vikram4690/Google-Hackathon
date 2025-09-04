# AI Trip Planner

This project is an AI-powered personalized trip planner for India, leveraging Google Vertex AI, Gemini, Maps API, Firebase, and BigQuery. It dynamically creates end-to-end itineraries tailored to individual budgets, interests, and real-time conditions, with seamless booking and payment capabilities.

## Features
- Dynamic itinerary generation (budget, duration, interests)
- Aggregates data from maps, events, local guides
- Multilingual, interactive interface
- Real-time smart adjustments (weather, delays, last-minute bookings)
- Shareable, optimized itinerary with cost breakdown
- One-click booking and payment

## Tech Stack
- Python 3.13+
- Google Vertex AI, Gemini
- Google Maps API
- Firebase
- BigQuery
- Flask or FastAPI (backend)

## Getting Started
1. Ensure Python 3.13+ is installed.
2. Set up Google Cloud APIs and credentials.
3. Install dependencies:
   ```sh
   pip install flask google-cloud-vertex-ai googlemaps firebase-admin google-cloud-bigquery
   ```
4. Run the backend server:
   ```sh
   python main.py
   ```

## Project Structure
- `main.py`: Entry point for the backend server
- `requirements.txt`: Python dependencies
- `.github/copilot-instructions.md`: Workspace instructions

## Next Steps
- Implement itinerary generation logic
- Integrate Google APIs
- Build booking and payment modules
- Develop frontend (optional)

---
Replace placeholder code and credentials with your own for production use.
