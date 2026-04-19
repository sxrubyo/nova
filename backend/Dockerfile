FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt nova_core_requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt
COPY nova ./nova
COPY nova.py ./nova.py
COPY frontend/dist ./frontend/dist
EXPOSE 8000
CMD ["python3", "nova.py", "serve", "--host", "0.0.0.0", "--port", "8000"]
