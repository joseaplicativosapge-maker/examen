import boto3
import json
import os

s3 = boto3.client(
    "s3",
    endpoint_url=os.environ.get("AWS_ENDPOINT_URL", None),
    region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
)

BUCKET = os.environ.get("S3_BUCKET", "country-pipeline-bucket")


def save_json(key: str, data: dict) -> str:
    s3.put_object(
        Bucket=BUCKET,
        Key=key,
        Body=json.dumps(data, ensure_ascii=False, indent=2),
        ContentType="application/json"
    )
    return f"s3://{BUCKET}/{key}"


def save_bytes(key: str, data: bytes, content_type: str = "application/pdf") -> str:
    s3.put_object(
        Bucket=BUCKET,
        Key=key,
        Body=data,
        ContentType=content_type
    )
    return f"s3://{BUCKET}/{key}"


def get_json(key: str) -> dict:
    response = s3.get_object(Bucket=BUCKET, Key=key)
    return json.loads(response["Body"].read())