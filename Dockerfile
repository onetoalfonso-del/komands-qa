FROM python:3.11-slim

# Instalar Node.js 20 + Newman
RUN apt-get update && apt-get install -y curl gnupg && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    npm install -g newman newman-reporter-htmlextra && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código fuente
COPY . .

EXPOSE 8001

CMD ["python", "test_runner.py"]
