FROM python:3.11-slim

RUN apt update && apt install -y curl && apt clean

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source code
COPY . .

# Flask environment variables
ENV FLASK_HOST=0.0.0.0
ENV FLASK_PORT=33079
ENV FLASK_DEBUG=False

# Expose Flask port
EXPOSE 33079

# Run the Flask app
CMD ["python3", "app.py"]