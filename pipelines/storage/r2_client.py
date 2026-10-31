import boto3
from boto3.s3.transfer import TransferConfig
from botocore.config import Config
from settings import get_settings


class R2Storage:
    def __init__(self):
        settings = get_settings()
        self._storage_client = boto3.client(
            service_name="s3",
            endpoint_url=f"https://{settings.cf_account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=settings.cf_account_access_id,
            aws_secret_access_key=settings.cf_secret_access_key.get_secret_value(),
            region_name="auto",
            config=Config(retries={"max_attempts": 5, "mode": "adaptive"}),
        )
        self._bucket_name = settings.cf_bucket_name
        self._transfer_config = TransferConfig(
            max_concurrency=settings.max_s3_workers,
            multipart_chunksize=settings.s3_part_upload_size,
            multipart_threshold=settings.s3_part_upload_size,
        )

    def upload_file(self, file_path: str, file_id: str, content_type: str):
        self._storage_client.upload_file(
            Filename=file_path,
            Bucket=self._bucket_name,
            Key=file_id,
            Config=self._transfer_config,
            ExtraArgs={"ContentType": content_type},
        )
