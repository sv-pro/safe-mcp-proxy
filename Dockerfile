FROM python:3.12-slim

WORKDIR /app

# Runtime dependencies
RUN pip install --no-cache-dir pyyaml fastapi uvicorn[standard]

COPY . .

# Create log directory (gitignored at runtime)
RUN mkdir -p safe_mcp_proxy/logs

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
