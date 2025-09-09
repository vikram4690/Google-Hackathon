# AI Trip Planner for India 🇮🇳

An AI-powered personalized trip planner for India, leveraging Google's Gemini model through Vertex AI. This application creates detailed, day-by-day travel itineraries based on user-specified requirements including origin, destination, dates, budget, interests, and more.

---

## 🚀 Features

* **Detailed User Input**: Collects trip origin, destination, dates, budget, multiple interests, preferred transport, and additional notes.
* **AI-Powered Itinerary Generation**: Uses a detailed prompt to instruct the **Gemini 1.5 Flash** model to generate a structured JSON response containing a day-by-day plan and cost breakdown.
* **Multi-Page Interface**:
    * A clean input form on the main page (`/`).
    * A dedicated results page (`/itinerary`) to display the generated plan.
* **Interactive Regeneration**: Users can provide feedback or request changes on the itinerary page, which triggers the AI to generate a revised plan.
* **Multilingual Support**: Capable of generating itineraries in multiple Indian languages.
* **User Feedback**: Provides a loading message during itinerary generation and helpful error messages for invalid input.

---

## 🛠️ Tech Stack

* **Backend**: Python 3.11+ with Flask
* **AI Model**: Google Gemini 1.5 Flash via Vertex AI
* **Frontend**: HTML5, CSS3, JavaScript
* **Deployment (Planned)**: Google Cloud Run with Gunicorn

---

## 📂 Project Structure

The project is organized as a standard Flask application:
```
.
├── app.py              # The main Flask application, contains all backend logic and routes.
├── requirements.txt      # A list of all necessary Python packages.
├── Dockerfile            # Instructions to containerize the app for deployment.
└── templates/
    ├── index.html      # The main page with the user input form.
    └── itinerary.html  # The page that displays the generated itinerary.
```

---

## 🏁 Getting Started (Local Development)

Follow these steps to run the application on your local machine.

### 1. Prerequisites

* Python (3.10+ recommended)
* An active Google Cloud Project with billing enabled.
* The [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) installed and authenticated.

### 2. Initial Setup
Clone the repository and navigate into the project directory.

Create and activate a Python virtual environment:
```bash
# Create the environment
python -m venv venv

# Activate on Windows (PowerShell)
.\venv\Scripts\activate

# Activate on macOS/Linux
source venv/bin/activate
```
Install the required Python packages:
```bash
pip install -r requirements.txt
```
### 3. Configure Google Cloud
Enable the necessary APIs in your project:

* Vertex AI API

Authenticate your local machine for Application Default Credentials (ADC):
```bash
gcloud auth application-default login
```
This will open a browser window for you to log in and grant permissions.

### 4. Set Environment Variables
You must set the following environment variable in your terminal before running the app.

On Windows (PowerShell):
```bash
$env:GOOGLE_PROJECT_ID = "your-gcp-project-id"
```
On macOS/Linux:
```bash
export GOOGLE_PROJECT_ID="your-gcp-project-id"
```
### 5. Run the Application
With your virtual environment active and environment variables set, start the Flask server:
```bash
flask run
```
