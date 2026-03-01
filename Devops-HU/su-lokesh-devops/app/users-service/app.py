"""
Users Service — CRUD for users table (id, name, email, role).
Port: 5001
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
SERVICE_NAME = "users-service"
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "5001"))
OTEL_COLLECTOR_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector.monitoring:4317")

DB_HOST = os.getenv("DB_HOST", "postgres-cluster.database")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "appdb")
DB_USER = os.getenv("DB_USER", "users_svc")
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
    """Create users table if it doesn't exist."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                role VARCHAR(100) NOT NULL DEFAULT 'user'
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
        logger.info("Database initialized — users table ready")
    except Exception as e:
        logger.error(f"Database init failed: {e}")


# -----------------------------------------------
# Routes
# -----------------------------------------------
@app.route("/health")
def health():
    return jsonify({"status": "healthy", "service": SERVICE_NAME}), 200


@app.route("/api/users", methods=["GET"])
def get_users():
    with tracer.start_as_current_span("get-all-users"):
        start = time.time()
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM users ORDER BY id")
        users = cur.fetchall()
        cur.close()
        conn.close()
        DB_QUERY_LATENCY.labels(operation="select_all").observe(time.time() - start)
        return jsonify(users), 200


@app.route("/api/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    with tracer.start_as_current_span("get-user"):
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        if user is None:
            return jsonify({"error": "User not found"}), 404
        return jsonify(user), 200


@app.route("/api/users", methods=["POST"])
def create_user():
    with tracer.start_as_current_span("create-user"):
        data = request.get_json()
        if not data or not all(k in data for k in ("name", "email")):
            return jsonify({"error": "name and email are required"}), 400
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute(
                "INSERT INTO users (name, email, role) VALUES (%s, %s, %s) RETURNING *",
                (data["name"], data["email"], data.get("role", "user"))
            )
            user = cur.fetchone()
            conn.commit()
            cur.close()
            conn.close()
            logger.info(f"User created: {user['id']}")
            return jsonify(user), 201
        except psycopg2.IntegrityError:
            return jsonify({"error": "Email already exists"}), 409


@app.route("/api/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    with tracer.start_as_current_span("update-user"):
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "UPDATE users SET name = COALESCE(%s, name), email = COALESCE(%s, email), role = COALESCE(%s, role) WHERE id = %s RETURNING *",
            (data.get("name"), data.get("email"), data.get("role"), user_id)
        )
        user = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if user is None:
            return jsonify({"error": "User not found"}), 404
        return jsonify(user), 200


@app.route("/api/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    with tracer.start_as_current_span("delete-user"):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE id = %s RETURNING id", (user_id,))
        deleted = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if deleted is None:
            return jsonify({"error": "User not found"}), 404
        logger.info(f"User deleted: {user_id}")
        return jsonify({"message": f"User {user_id} deleted"}), 200


@app.route("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


if __name__ == "__main__":
    init_db()
    logger.info(f"Starting {SERVICE_NAME} on port {SERVICE_PORT}")
    app.run(host="0.0.0.0", port=SERVICE_PORT, debug=False)
