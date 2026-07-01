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

# Credenciales APIM — pasadas como build args desde Railway service variables
ARG SN_CONSUMER_KEY=""
ARG SN_CONSUMER_SECRET=""
ARG APIM_URL="https://epreapi.onnetfibra.cl"
RUN python3 -c "\
import json, os, sys; \
ck=sys.argv[1]; cs=sys.argv[2]; url=sys.argv[3]; \
open('/app/apim-config.json','w').write(json.dumps({'ck':ck,'cs':cs,'url':url})) if ck and cs else None \
" "$SN_CONSUMER_KEY" "$SN_CONSUMER_SECRET" "$APIM_URL"

EXPOSE 8001

CMD ["python", "test_runner.py"]
