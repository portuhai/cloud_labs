import os
import json
import time
import psycopg2
import redis
import boto3

DATABASE_URL = os.environ.get("DATABASE_URL")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
SQS_QUEUE_URL = os.environ.get("SQS_QUEUE_URL")
AWS_REGION = os.environ.get("AWS_REGION", "eu-central-1")

try:
    redis_client = redis.Redis.from_url(REDIS_URL)
    redis_client.ping()
except Exception as e:
    print(f"Worker Redis warning: {e}")
    redis_client = None

sqs_client = boto3.client("sqs", region_name=AWS_REGION) if SQS_QUEUE_URL else None


def get_db_connection():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    return psycopg2.connect(DATABASE_URL)


def process_message(body_str: str):
    data = json.loads(body_str)
    request_id = data.get("request_id")
    text = data.get("text", "")

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
            # Ідемпотентний запис: при повторній доставці того самого request_id дублікат не створиться
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
            print(f"Worker Redis cache invalidation warning: {e}")


def run_worker():
    print("Starting async queue worker...")
    if not sqs_client or not SQS_QUEUE_URL:
        print("SQS_QUEUE_URL is not configured. Worker idle.")
        while True:
            time.sleep(10)

    while True:
        try:
            response = sqs_client.receive_message(
                QueueUrl=SQS_QUEUE_URL,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=15,
            )
            messages = response.get("Messages", [])
            for msg in messages:
                receipt_handle = msg["ReceiptHandle"]
                try:
                    process_message(msg["Body"])
                    sqs_client.delete_message(
                        QueueUrl=SQS_QUEUE_URL,
                        ReceiptHandle=receipt_handle,
                    )
                    print(f"Processed and deleted message: {msg.get('MessageId')}")
                except Exception as e:
                    # Не видаляємо повідомлення з черги при помилці — після visibility timeout воно повернеться
                    print(f"Failed to process message {msg.get('MessageId')}: {e}")
        except Exception as e:
            print(f"SQS poll error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    run_worker()