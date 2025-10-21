# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the dependencies file to the working directory
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code to the working directory
COPY rest_script2.py .

# Make port 8501 available to the world outside this container
EXPOSE 8501

# Define environment variable for the port
ENV PORT 8501

# Run the application
CMD ["streamlit", "run", "rest_script2.py", "--server.port", "8501", "--server.enableCORS", "false"]
