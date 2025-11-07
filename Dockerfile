# Use an official lightweight Python image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /GOOGLE-HACKATHON

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Set the command to run the application using gunicorn
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app
