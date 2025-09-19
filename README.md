---

# AI Trip Planner for India 🇮🇳

An advanced, AI-powered personalized trip planner for India. This application creates detailed, day-by-day travel itineraries based on user requirements and integrates real-world data for realistic budgeting. It features a complete user account system for saving, viewing, and booking trips.

---

## 🚀 Features

### Core AI & Planning
*   **AI-Powered Itinerary Generation**: Uses **Gemini 1.5 Flash** via Vertex AI to generate structured, day-by-day travel plans.
*   **Realistic Budgeting with Tool Use**: The AI doesn't guess! It uses a custom "tool" to call a live Booking.com API, retrieve real-time average hotel prices for the destination, and build a budget around that data.
*   **Interactive Regeneration**: Users can request changes to a generated itinerary, and the AI will provide a revised plan.
*   **Mapping Integration**: Displays activity locations on an embedded Google Map for easy visualization.
*   **Multilingual Support**: Capable of generating itineraries in multiple Indian languages.

### User Accounts & Dashboard
*   **Secure User Authentication**: Full user registration and login system powered by **Firebase Authentication**.
*   **Personal User Dashboard**: A secure, multi-tab dashboard for logged-in users.
    *   **Overview Tab**: At-a-glance summary of total saved and booked trips.
    *   **My Trips Tab**: A complete list of all saved trips, with status badges ("Planned" or "Booked").
    *   **Booking History Tab**: A dedicated view showing only booked trips.
    *   **Profile Management**: Users can view their email and update their display name.
*   **Clickable Trip Details**: Saved trips on the dashboard are clickable, leading to a full, detailed view of the saved itinerary.

### Booking & Data Persistence
*   **Serverless Backend**: Uses **Google Cloud Functions** for secure and scalable database operations (`save-trip`, `get-trips`, `book-trip`).
*   **Persistent Trip Storage**: User itineraries are securely saved to a **Cloud Firestore** database, linked to their user ID.
*   **Complete Booking Flow**: Users can proceed from a saved trip to a payment page and "book" their trip, which updates its status in the database from `planned` to `booked`.

---

## 🏗️ Architecture & Tech Stack

This project uses a modern, cloud-native architecture.

*   **Frontend**: HTML5, CSS3, JavaScript
*   **Backend Web Server**: Python with **Flask**
*   **AI Core**: **Vertex AI** (Gemini 1.5 Flash with Tool Use / Function Calling)
*   **Authentication**: **Firebase Authentication**
*   **Database**: **Cloud Firestore** (NoSQL)
*   **Serverless Backend**: **Google Cloud Functions** (Python)
*   **Mapping**: **Google Maps Platform** (Maps JavaScript API)
*   **External Data**: **RapidAPI** (Booking.com API for real-time pricing)
*   **Deployment (Planned)**: **Google Cloud Run** with Gunicorn

---

## 📂 Project Structure

Your project now has a comprehensive structure separating the web app from the serverless functions:

```
.
├── __pycache__/
├── cloud_functions/
│   ├── save-trip/
│   ├── get-trips/
│   └── book-trip/
├── templates/
│   ├── index.html
│   ├── login.html
│   ├── signup.html
│   ├── dashboard.html
│   ├── itinerary.html
│   ├── trip_details.html
│   ├── payment.html
│   └── booking_success.html
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

Clone the repository and create/activate a Python virtual environment:
```bash
# Create the environment
python -m venv venv

# Activate on Windows
.\venv\Scripts\activate

# Activate on macOS/Linux
source venv/bin/activate
```
Install the required packages for the main Flask app:
```bash
pip install -r requirements.txt
```

### 3. Configure Google Cloud & Firebase

1.  **Enable APIs**: In your Google Cloud project, enable the following APIs: **Vertex AI, Cloud Functions, Cloud Build, Cloud Run, Artifact Registry, Cloud Firestore, Identity Toolkit (Firebase Auth), and Places API**.
2.  **Firebase Setup**:
    *   Go to the Firebase Console for your project.
    *   Enable **Authentication** with the "Email/Password" provider.
    *   Enable **Cloud Firestore** in Production mode.
3.  **Service Account Key**: In your GCP project settings under "Service Accounts", create a new service account key and download the JSON file. Rename it to `serviceAccountKey.json` and place it in your project's root directory.
4.  **Authenticate CLI**: Authenticate your local machine for both gcloud and Application Default Credentials (ADC):
    ```bash
    gcloud auth login
    gcloud auth application-default login
    ```

### 4. Set Environment Variables

Create a file named `.env` in the root of your project and add the following keys. **This file should be in your `.gitignore`!**

```
# .env file

# Your Google Cloud Project ID
GOOGLE_PROJECT_ID="your-gcp-project-id"

# Your API key for Google Maps Platform
GOOGLE_MAPS_API_KEY="your-google-maps-api-key"

# Your API key from RapidAPI for the Booking.com API
RAPIDAPI_KEY="your-rapidapi-key"
```

### 5. Deploy Cloud Functions

Before running the web app, you must deploy your serverless functions. For each folder inside `cloud_functions/` (`save-trip`, `get-trips`, `book-trip`), run the deployment command.

**Example for `save-trip`:**
```bash
# Navigate into the function's directory
cd cloud_functions/save-trip

# Deploy the function (use the correct region and entry point for each)
gcloud functions deploy save-trip --runtime python311 --trigger-http --entry-point save_trip_to_firestore --allow-unauthenticated --region asia-south1

# Navigate back out
cd ../..
```
Repeat this process for `get-trips` and `book-trip`, using their respective names and entry points.

### 6. Update `app.py` with Function URLs

After deploying the functions, copy their trigger URLs from the command line output and paste them into the corresponding constants at the top of your `app.py` file.

```python
# app.py
SAVE_TRIP_FUNCTION_URL = "https://your-url-for-save-trip..."
GET_TRIPS_FUNCTION_URL = "https://your-url-for-get-trips..."
BOOK_TRIP_FUNCTION_URL = "https://your-url-for-book-trip..."
```

### 7. Run the Application

With all configurations complete, start the Flask server:
```bash
flask run
```
Your application will now be running locally, fully connected to your live cloud services.
