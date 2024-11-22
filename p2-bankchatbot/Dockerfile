# Base image with Python 3.9
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Upgrade pip and install torch with the extra index URL
RUN pip install --upgrade pip && \
    pip install torch==2.0.1+cpu -f https://download.pytorch.org/whl/torch_stable.html

# Install the rest of the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container
COPY . .

# Download the DialoGPT-small model during the build
RUN python -c "from transformers import AutoModelForCausalLM, AutoTokenizer; \
    AutoTokenizer.from_pretrained('microsoft/DialoGPT-small'); \
    AutoModelForCausalLM.from_pretrained('microsoft/DialoGPT-small')"

# Expose the port (Cloud Run uses the PORT environment variable)
EXPOSE 8080

# Set the PORT environment variable
ENV PORT=8080

# Command to run the Flask app using Gunicorn
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 server:app"]
