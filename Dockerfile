FROM python:3.10-slim

WORKDIR /app

# Instalar dependências de sistema necessárias para o Pillow e fontes
RUN apt-get update && apt-get install -y \
    gcc \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primeiro para cache do docker
COPY backend/requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Definir o fuso horário (America/Sao_Paulo)
ENV TZ=America/Sao_Paulo
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Copiar todo o código
COPY . .

# Expor a porta que a API vai rodar
EXPOSE 8000

# Comando para iniciar o servidor
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
