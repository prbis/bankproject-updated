# Use the official Python image
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the required Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application into the container
COPY . .

# Set environment variables
ENV FLASK_APP=server111.py
ENV FLASK_ENV=production

# Expose the port the app runs on
EXPOSE 8080

# Run the Flask app
CMD ["flask", "run", "--host=0.0.0.0", "--port=8080"]
