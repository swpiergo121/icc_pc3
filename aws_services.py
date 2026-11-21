#!/usr/bin/env python3

import json
import os

import boto3

from dotenv import load_dotenv

load_dotenv()  # Loads .env before the variables below are read


REGION = os.getenv("AWS_REGION", "us-east-1")
ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL") or None  # http://localstack:4566 en local
BUCKET = os.getenv("S3_BUCKET", "tienda-imagenes")
PRODUCTS_TABLE = os.getenv("PRODUCTS_TABLE", "products")
ORDERS_TABLE = os.getenv("ORDERS_TABLE", "orders")
QUEUE_NAME = os.getenv("ORDERS_QUEUE", "orders-queue")
SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL", "")

_kw = {"region_name": REGION, "endpoint_url": ENDPOINT_URL}

dynamodb = boto3.resource("dynamodb", **_kw)
s3 = boto3.client("s3", **_kw)
sqs = boto3.client("sqs", **_kw)

products_t = dynamodb.Table(PRODUCTS_TABLE)
orders_t = dynamodb.Table(ORDERS_TABLE)


def upload_image(file_stream, key, content_type):
    s3.upload_fileobj(file_stream, BUCKET, key, ExtraArgs={"ContentType": content_type})


def get_image(key):
    return s3.get_object(Bucket=BUCKET, Key=key)


def _queue_url():
    return SQS_QUEUE_URL or sqs.get_queue_url(QueueName=QUEUE_NAME)["QueueUrl"]


def send_order_message(order):
    sqs.send_message(QueueUrl=_queue_url(), MessageBody=json.dumps(order, default=str))


def update_order_status(order_id, status):
    orders_t.update_item(
        Key={"id": order_id},
        UpdateExpression="SET #s = :s",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":s": status},
    )
