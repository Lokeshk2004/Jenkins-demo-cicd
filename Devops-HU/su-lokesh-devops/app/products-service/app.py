"""
Products Service — CRUD for products table (id, name, price, category).
Port: 5002
"""

import os
import json
import logging
import time

import psycopg2
import psycopg2.extras
from flask import Flask, request, jsonify
from prometheus_client import (
    Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
)
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.sdk.resources import Resource
from pythonjsonlogger import jsonlogger

# -----------------------------------------------
# Configuration
# -----------------------------------------------
SERVICE_NAME = "products-service"
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "5002"))
OTEL_COLLECTOR_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector.monitoring:4317")

DB_HOST = os.getenv("DB_HOST", "postgres-cluster.database")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "appdb")
DB_USER = os.getenv("DB_USER", "products_svc")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

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
Psycopg2Instrumentor().instrument()

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
DB_QUERY_LATENCY = Histogram(
    "db_query_duration_seconds",
    "Database query latency in seconds",
    ["operation"]
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
# Database Helper
# -----------------------------------------------
def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASSWORD
    )


def init_db():
    """Create products table if it doesn't exist."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                price DECIMAL(10, 2) NOT NULL,
                category VARCHAR(100) NOT NULL
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
        logger.info("Database initialized — products table ready")
    except Exception as e:
        logger.error(f"Database init failed: {e}")


# -----------------------------------------------
# Routes
# -----------------------------------------------
@app.route("/health")
def health():
    return jsonify({"status": "healthy", "service": SERVICE_NAME}), 200


@app.route("/api/products", methods=["GET"])
def get_products():
    with tracer.start_as_current_span("get-all-products"):
        start = time.time()
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM products ORDER BY id")
        products = cur.fetchall()
        cur.close()
        conn.close()
        DB_QUERY_LATENCY.labels(operation="select_all").observe(time.time() - start)
        # Convert Decimal to float for JSON serialization
        for p in products:
            p["price"] = float(p["price"])
        return jsonify(products), 200


@app.route("/api/products/<int:product_id>", methods=["GET"])
def get_product(product_id):
    with tracer.start_as_current_span("get-product"):
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM products WHERE id = %s", (product_id,))
        product = cur.fetchone()
        cur.close()
        conn.close()
        if product is None:
            return jsonify({"error": "Product not found"}), 404
        product["price"] = float(product["price"])
        return jsonify(product), 200


@app.route("/api/products", methods=["POST"])
def create_product():
    with tracer.start_as_current_span("create-product"):
        data = request.get_json()
        if not data or not all(k in data for k in ("name", "price", "category")):
            return jsonify({"error": "name, price, and category are required"}), 400
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute(
                "INSERT INTO products (name, price, category) VALUES (%s, %s, %s) RETURNING *",
                (data["name"], data["price"], data["category"])
            )
            product = cur.fetchone()
            conn.commit()
            cur.close()
            conn.close()
            product["price"] = float(product["price"])
            logger.info(f"Product created: {product['id']}")
            return jsonify(product), 201
        except Exception as e:
            logger.error(f"Create product failed: {e}")
            return jsonify({"error": str(e)}), 500


@app.route("/api/products/<int:product_id>", methods=["PUT"])
def update_product(product_id):
    with tracer.start_as_current_span("update-product"):
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """UPDATE products
               SET name = COALESCE(%s, name),
                   price = COALESCE(%s, price),
                   category = COALESCE(%s, category)
               WHERE id = %s RETURNING *""",
            (data.get("name"), data.get("price"), data.get("category"), product_id)
        )
        product = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if product is None:
            return jsonify({"error": "Product not found"}), 404
        product["price"] = float(product["price"])
        return jsonify(product), 200


@app.route("/api/products/<int:product_id>", methods=["DELETE"])
def delete_product(product_id):
    with tracer.start_as_current_span("delete-product"):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM products WHERE id = %s RETURNING id", (product_id,))
        deleted = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if deleted is None:
            return jsonify({"error": "Product not found"}), 404
        logger.info(f"Product deleted: {product_id}")
        return jsonify({"message": f"Product {product_id} deleted"}), 200


@app.route("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


if __name__ == "__main__":
    init_db()
    logger.info(f"Starting {SERVICE_NAME} on port {SERVICE_PORT}")
    app.run(host="0.0.0.0", port=SERVICE_PORT, debug=False)
