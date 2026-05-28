# Use the official Playwright Python image which includes all browser dependencies
FROM mcr.microsoft.com/playwright/python:v1.52.0-jammy

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV HEADLESS=true
ENV PORT=8000

# Set the working directory
WORKDIR /app

# Copy requirements and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose the port the app runs on
EXPOSE 8000

# Start the FastAPI server using Uvicorn
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT}