import os
import datetime
import json
import uuid
from functools import wraps
from flask import Flask, request
from flask_restx import Api, Resource, fields
import psycopg2
import jwt
import redis
import boto3

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
SQS_QUEUE_URL = os.environ.get("SQS_QUEUE_URL")
AWS_REGION = os.environ.get("AWS_REGION", "eu-central-1")
JWT_SECRET = os.environ.get("JWT_SECRET", "dev-fallback-secret-change-in-prod")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

try:
    redis_client = redis.Redis.from_url(REDIS_URL)
    redis_client.ping()
except Exception as e:
    print(f"Redis connection warning: {e}")
    redis_client = None

sqs_client = boto3.client("sqs", region_name=AWS_REGION) if SQS_QUEUE_URL else None

CACHE_TTL = 45

authorizations = {
    "Bearer": {
        "type": "apiKey",
        "in": "header",
        "name": "Authorization",
        "description": "Введіть токен у форматі: Bearer <ваш_JWT_токен>",
    }
}

api = Api(
    app,
    version="1.0",
    title="Cloud Lab Async Queue API",
    description="REST API з PostgreSQL, Redis Cache-Aside, JWT та асинхронною чергою SQS",
    authorizations=authorizations,
    security="Bearer",
    doc="/docs",
)

ns = api.namespace("api", description="Основні операції з повідомленнями")

login_model = api.model("Login", {
    "username": fields.String(required=True, example="admin"),
    "password": fields.String(required=True, example="admin123"),
})

message_model = api.model("Message", {
    "text": fields.String(required=True, example="Асинхронне повідомлення в чергу!"),
})


def get_db_connection():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    return psycopg2.connect(DATABASE_URL)


def init_db():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS messages (
                        id SERIAL PRIMARY KEY,
                        request_id TEXT UNIQUE,
                        text TEXT NOT NULL
                    );
                    """
                )
                cur.execute(
                    """
                    ALTER TABLE messages
                    ADD COLUMN IF NOT EXISTS request_id TEXT UNIQUE;
                    """
                )
    except Exception as e:
        print(f"DB init warning: {e}")


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return {"error": "Missing or invalid Authorization header"}, 401

        token = auth_header.split(" ", 1)[1]
        try:
            jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return {"error": "Token has expired"}, 401
        except jwt.InvalidTokenError:
            return {"error": "Invalid token"}, 401

        return f(*args, **kwargs)

    return decorated


@ns.route("/login")
class LoginResource(Resource):
    @ns.expect(login_model)
    def post(self):
        """Отримати JWT-токен для доступу до захищених ендпоінтів"""
        data = request.json or {}
        if data.get("username") == "admin" and data.get("password") == ADMIN_PASSWORD:
            payload = {
                "sub": "admin",
                "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=2),
            }
            token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
            return {"token": token}, 200
        return {"error": "Invalid credentials"}, 401


@ns.route("/data")
class DataResource(Resource):
    @ns.doc("get_data", security=None)
    def get(self):
        """Отримати всі записи з БД (з використанням Cache-Aside Redis)"""
        cache_key = "cache:messages:all"

        if redis_client:
            try:
                cached_data = redis_client.get(cache_key)
                if cached_data:
                    return json.loads(cached_data), 200
            except Exception as e:
                print(f"Redis read error: {e}")

        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT id, request_id, text FROM messages ORDER BY id;")
                    rows = cur.fetchall()

            result = [{"id": r[0], "request_id": r[1], "text": r[2]} for r in rows]

            if redis_client:
                try:
                    redis_client.setex(cache_key, CACHE_TTL, json.dumps(result))
                except Exception as e:
                    print(f"Redis write error: {e}")

            return result, 200
        except Exception as e:
            return {"error": str(e)}, 500

    @ns.doc("post_data")
    @ns.expect(message_model)
    @token_required
    def post(self):
        """Покласти повідомлення в чергу та одразу повернути 202 Accepted"""
        data = request.json or {}
        text = data.get("text", "").strip()
        if not text:
            return {"error": "Field 'text' is required"}, 400

        request_id = str(uuid.uuid4())
        payload = {
            "request_id": request_id,
            "text": text,
        }

        try:
            if sqs_client and SQS_QUEUE_URL:
                sqs_client.send_message(
                    QueueUrl=SQS_QUEUE_URL,
                    MessageBody=json.dumps(payload),
                )
            else:
                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            INSERT INTO messages (request_id, text)
                            VALUES (%s, %s)
                            ON CONFLICT (request_id) DO NOTHING;
                            """,
                            (request_id, text),
                        )

            if redis_client:
                try:
                    redis_client.delete("cache:messages:all")
                except Exception as e:
                    print(f"Redis delete error: {e}")

            return {
                "status": "queued",
                "request_id": request_id,
                "message": "Accepted for asynchronous processing",
            }, 202
        except Exception as e:
            return {"error": str(e)}, 500


@app.route("/health")
def health():
    return {"status": "healthy"}, 200


@app.route("/")
def index():
    return {"message": "Cloud Lab Async Queue API is running. Go to /docs for Swagger UI."}, 200


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)