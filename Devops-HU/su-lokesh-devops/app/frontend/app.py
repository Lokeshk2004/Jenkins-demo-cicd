"""
Frontend Service — Flask UI that proxies API calls to backend services.
Port: 5000
"""

import os
import json
import logging
import time

import requests
from flask import Flask, request, jsonify, render_template_string
from prometheus_client import (
    Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
)
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import Resource
from pythonjsonlogger import jsonlogger

# -----------------------------------------------
# Configuration
# -----------------------------------------------
SERVICE_NAME = "frontend"
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "5000"))
USERS_SERVICE_URL = os.getenv("USERS_SERVICE_URL", "http://users-svc.backend-users:5001")
PRODUCTS_SERVICE_URL = os.getenv("PRODUCTS_SERVICE_URL", "http://products-svc.backend-products:5002")
ORDERS_SERVICE_URL = os.getenv("ORDERS_SERVICE_URL", "http://orders-svc.backend-orders:5003")
OTEL_COLLECTOR_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector.monitoring:4317")

# -----------------------------------------------
# Structured JSON Logging
# -----------------------------------------------
logger = logging.getLogger(SERVICE_NAME)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(
    fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
    rename_fields={"asctime": "timestamp", "levelname": "level", "name": "service"}
)
handler.setFormatter(formatter)
logger.addHandler(handler)

# -----------------------------------------------
# OpenTelemetry Setup
# -----------------------------------------------
resource = Resource.create({"service.name": SERVICE_NAME})
provider = TracerProvider(resource=resource)
otlp_exporter = OTLPSpanExporter(endpoint=OTEL_COLLECTOR_ENDPOINT, insecure=True)
provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer(SERVICE_NAME)

# -----------------------------------------------
# Flask App
# -----------------------------------------------
app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()

# -----------------------------------------------
# Prometheus Metrics
# -----------------------------------------------
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"]
)


@app.before_request
def start_timer():
    request._start_time = time.time()


@app.after_request
def record_metrics(response):
    latency = time.time() - getattr(request, "_start_time", time.time())
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.path,
        status=response.status_code
    ).inc()
    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=request.path
    ).observe(latency)

    # Inject trace context into logs
    span = trace.get_current_span()
    ctx = span.get_span_context()
    logger.info(
        "request_completed",
        extra={
            "trace_id": format(ctx.trace_id, "032x") if ctx.trace_id else "",
            "span_id": format(ctx.span_id, "016x") if ctx.span_id else "",
            "method": request.method,
            "path": request.path,
            "status": response.status_code,
            "latency_ms": round(latency * 1000, 2)
        }
    )
    return response


# -----------------------------------------------
# HTML Template
# -----------------------------------------------
INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SU DevOps Platform</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #0f172a; color: #e2e8f0; }
        .container { max-width: 1200px; margin: 0 auto; padding: 2rem; }
        h1 { color: #38bdf8; margin-bottom: 1rem; font-size: 2rem; }
        .card { background: #1e293b; border-radius: 12px; padding: 1.5rem; margin: 1rem 0; border: 1px solid #334155; }
        .card h2 { color: #7dd3fc; margin-bottom: 0.5rem; }
        .status { display: inline-block; padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.85rem; }
        .status.up { background: #065f46; color: #6ee7b7; }
        .status.down { background: #7f1d1d; color: #fca5a5; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1rem; }
        a { color: #38bdf8; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 SU DevOps Platform — Frontend</h1>
        <p>Microservices Dashboard</p>
        <div class="grid">
            <div class="card">
                <h2>👤 Users Service</h2>
                <p>CRUD operations for users</p>
                <p><a href="/api/users">/api/users</a></p>
            </div>
            <div class="card">
                <h2>📦 Products Service</h2>
                <p>CRUD operations for products</p>
                <p><a href="/api/products">/api/products</a></p>
            </div>
            <div class="card">
                <h2>🛒 Orders Service</h2>
                <p>CRUD operations for orders</p>
                <p><a href="/api/orders">/api/orders</a></p>
            </div>
            <div class="card">
                <h2>💚 Health Check</h2>
                <p><a href="/health">/health</a></p>
            </div>
        </div>
    </div>
</body>
</html>
"""


# -----------------------------------------------
# Routes
# -----------------------------------------------
@app.route("/")
def index():
    return render_template_string(INDEX_HTML)


@app.route("/health")
def health():
    return jsonify({"status": "healthy", "service": SERVICE_NAME}), 200


@app.route("/api/users", defaults={"path": ""}, methods=["GET", "POST"])
@app.route("/api/users/<path:path>", methods=["GET", "PUT", "DELETE"])
def proxy_users(path):
    url = f"{USERS_SERVICE_URL}/api/users/{path}".rstrip("/")
    return _proxy_request(url)


@app.route("/api/products", defaults={"path": ""}, methods=["GET", "POST"])
@app.route("/api/products/<path:path>", methods=["GET", "PUT", "DELETE"])
def proxy_products(path):
    url = f"{PRODUCTS_SERVICE_URL}/api/products/{path}".rstrip("/")
    return _proxy_request(url)


@app.route("/api/orders", defaults={"path": ""}, methods=["GET", "POST"])
@app.route("/api/orders/<path:path>", methods=["GET", "PUT", "DELETE"])
def proxy_orders(path):
    url = f"{ORDERS_SERVICE_URL}/api/orders/{path}".rstrip("/")
    return _proxy_request(url)


def _proxy_request(url):
    """Forward the incoming request to a backend service."""
    with tracer.start_as_current_span(f"proxy-{request.method}-{url}"):
        try:
            resp = requests.request(
                method=request.method,
                url=url,
                headers={k: v for k, v in request.headers if k.lower() != "host"},
                data=request.get_data(),
                params=request.args,
                timeout=10
            )
            return (resp.content, resp.status_code, resp.headers.items())
        except requests.exceptions.RequestException as e:
            logger.error(f"Proxy error: {e}", extra={"target_url": url})
            return jsonify({"error": "Service unavailable", "detail": str(e)}), 503


@app.route("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


if __name__ == "__main__":
    logger.info(f"Starting {SERVICE_NAME} on port {SERVICE_PORT}")
    app.run(host="0.0.0.0", port=SERVICE_PORT, debug=False)
