FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY mozhi_yansuan ./mozhi_yansuan
RUN pip install --no-cache-dir .

EXPOSE 8080
CMD ["python", "-m", "mozhi_yansuan", "serve", "--host", "0.0.0.0"]
