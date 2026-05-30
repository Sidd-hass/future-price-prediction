FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (if any)
# (none needed for pure python)

# Copy requirement file and install python packages
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application source code
COPY . ./

# Ensure the config file is present (you can mount it as a volume at runtime)
# Set environment variables for unbuffered output (helps Docker logs)
ENV PYTHONUNBUFFERED=1

# Default command runs the continuous scanner. Use --force if you want to run outside market hours.
CMD ["python", "main.py", "--force"]