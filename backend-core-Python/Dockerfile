# Imagem base leve com Python
FROM python:3.10-slim

# Instala ferramentas de sistema necessárias
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instala as bibliotecas de trading
RUN pip install --no-cache-dir ccxt python-dotenv requests

# Copia o código do robô para dentro do Docker
COPY . .

# Comando para iniciar o robô
CMD ["python", "main.py"]