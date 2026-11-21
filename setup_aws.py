#!/usr/bin/env python3

import time

from botocore.exceptions import ClientError

from dotenv import load_dotenv
load_dotenv()


from aws_services import (
    BUCKET, ORDERS_TABLE, PRODUCTS_TABLE, QUEUE_NAME, REGION,
    dynamodb, s3, sqs,
)


def wait_for_aws(retries=30):
    for i in range(retries):
        try:
            s3.list_buckets()
            return
        except Exception:
            print(f"Esperando AWS/LocalStack ({i + 1}/{retries})...", flush=True)
            time.sleep(2)
    raise SystemExit("No se pudo conectar con AWS/LocalStack")


def ensure_table(name):
    try:
        dynamodb.create_table(
            TableName=name,
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        print("Tabla creada:", name)
    except ClientError as e:
        if e.response["Error"]["Code"] != "ResourceInUseException":
            raise
        print("Tabla ya existe:", name)


def ensure_bucket():
    kwargs = {} if REGION == "us-east-1" else {
        "CreateBucketConfiguration": {"LocationConstraint": REGION}
    }
    try:
        s3.create_bucket(Bucket=BUCKET, **kwargs)
        print("Bucket creado:", BUCKET)
    except ClientError as e:
        if e.response["Error"]["Code"] not in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
            raise
        print("Bucket ya existe:", BUCKET)


if __name__ == "__main__":
    wait_for_aws()
    ensure_table(PRODUCTS_TABLE)
    ensure_table(ORDERS_TABLE)
    ensure_bucket()
    sqs.create_queue(QueueName=QUEUE_NAME)  # idempotente
    print("Cola SQS lista:", QUEUE_NAME)
