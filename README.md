---

# AI Trip Planner for India 🇮🇳

An advanced, AI-powered personalized trip planner for India. This application creates detailed, day-by-day travel itineraries based on user requirements and integrates real-world data for realistic budgeting and weather-aware planning. It features a complete user account system for saving, viewing, booking, sharing, and exporting trips.

---

## 🚀 Features

### Core AI & Planning
*   **AI-Powered Itinerary Generation**: Uses **Gemini 1.5 Flash** via Vertex AI to generate structured, day-by-day travel plans.
*   **Realistic Budgeting (Tool Use)**: Integrates with the Booking.com API to provide real-time average hotel prices, which the AI uses to create a realistic budget.
*   **Real-time Weather Adjustment (Tool Use)**: A button on the trip details page allows the AI to use the **OpenWeather API** to fetch current weather and suggest real-time adjustments to the day's activities.
*   **Interactive Regeneration**: Users can request changes to an itinerary, and the AI will provide a revised plan.
*   **Multilingual Support**: Capable of generating itineraries in multiple Indian languages.

### User Accounts & Dashboard
*   **Secure User Authentication**: Full user registration and login system powered by **Firebase Authentication**.
*   **Personal User Dashboard**: A secure, multi-tab dashboard for logged-in users with an overview of trips, a full list of saved trips, and profile management.
*   **Clickable Trip Details**: Saved trips on the dashboard are clickable, leading to a full, detailed view of the saved itinerary.

### Data Persistence, Sharing & Export
*   **Serverless Backend**: Uses **Google Cloud Functions** for secure and scalable database operations.
*   **Persistent Trip Storage**: Securely saves user itineraries to a **Cloud Firestore** database.
*   **Complete Booking Flow**: A full workflow from planning and saving to "booking" a trip, with status updates reflected on the dashboard.
*   **Public Trip Sharing**: Generate a unique, shareable public link for any saved trip.
*   **QR Code Generation**: Automatically creates a QR code for easy mobile sharing of trip links.
*   **PDF Export**: Download a beautifully formatted PDF document of your complete trip itinerary.

---

## 🛠️ Tech Stack

*   **Backend**: Python 3.11+ with **Flask**
*   **AI Core**: **Google Vertex AI** (Gemini 1.5 Flash with Tool Use)
*   **Frontend**: HTML5, CSS3, JavaScript
*   **Authentication**: **Firebase Authentication**
*   **Database**: **Cloud Firestore**
*   **Serverless Backend**: **Google Cloud Functions**
*   **External Data**: **RapidAPI** (Booking.com), **OpenWeather API**
*   **PDF/QR Generation**: **ReportLab**, **qrcode[pil]**
*   **Deployment**: **Google Cloud Run** with Gunicorn

---

## 📂 Project Structure

```
.
├── __pycache__/
├── cloud_functions/
│   ├── save-trip/
│   ├── get-trips/
│   └── book-trip/
├── templates/
│   ├── index.html, login.html, signup.html, dashboard.html,
│   ├── itinerary.html, trip_details.html, payment.html,
│   └── booking_success.html, share_success.html, ...
├── .env
├── .gitignore
├── app.py
├── Dockerfile
├── README.md
├── requirements.txt
├── serviceAccountKey.json
└── stepstorun.txt
```

---

## 🏁 Getting Started (Local Development)

### 1. Prerequisites

*   Python 3.11+
*   An active Google Cloud Project with billing enabled.
*   The [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) installed.

### 2. Initial Setup

Clone the repository, then create and activate a Python virtual environment:
```bash
# Create the environment
python -m venv venv

# Activate on Windows
.\venv\Scripts\activate

# Activate on macOS/Linux
source venv/bin/activate
```
Install the required Python packages:
```bash
pip install -r requirements.txt
```

### 3. Configure Google Cloud & Firebase

1.  **Enable APIs**: In your Google Cloud project, enable: **Vertex AI**, **Cloud Functions**, **Cloud Build**, **Cloud Run**, and **Cloud Firestore**.
2.  **Firebase Setup**: In the Firebase Console, enable **Authentication** (with Email/Password provider) and **Cloud Firestore** (in Production mode).
3.  **Service Account**: Create a service account key (JSON) in your GCP project and save it as `serviceAccountKey.json` in the project root.
4.  **Authenticate CLI**:
    ```bash
    gcloud auth login
    gcloud auth application-default login
    ```

### 4. Set Environment Variables

Create a file named `.env` in the root directory and add your secret keys.
```
# .env file
GOOGLE_PROJECT_ID="your-gcp-project-id"
RAPIDAPI_KEY="your-rapidapi-key"
OPENWEATHER_API_KEY="your-openweather-api-key"
```

### 5. Deploy Cloud Functions

Before running the app, deploy the serverless functions. For each folder in `cloud_functions/` (`save-trip`, `get-trips`, `book-trip`, etc.), navigate into it and run the deploy command.

**Example for `save-trip`:**
```bash
cd cloud_functions/save-trip
gcloud functions deploy save-trip --runtime python311 --trigger-http --entry-point save_trip_to_firestore --allow-unauthenticated --region asia-south1
cd ../..
```
Update the function URLs at the top of `app.py` with the trigger URLs from the deployment output.

### 6. Run the Application

With your virtual environment active, start the Flask server:
```bash
flask run
```
