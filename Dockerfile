FROM python:3.11-slim

WORKDIR /app

# Instalar dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Criar diretório de logs
RUN mkdir -p /app/logs

# Copiar o código da aplicação
COPY . .

# Expor a porta explicitamente
EXPOSE 5000

# Configurar variáveis de ambiente para logging
ENV PYTHONUNBUFFERED=1

# Comando para iniciar a aplicação com redirecionamento de logs
CMD ["python", "-u", "app.py"]
