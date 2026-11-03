FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    U2NET_HOME=/models

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

# Bake the default model into the image so cold starts don't download ~170MB.
RUN python -c "from rembg import new_session; new_session('u2net')"

COPY . .
EXPOSE 8080
CMD ["python", "main.py"]
