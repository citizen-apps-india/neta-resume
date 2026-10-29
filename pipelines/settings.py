from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    cf_account_id: str
    cf_secret_access_key: SecretStr
    cf_account_access_id: str

    cf_bucket_name: str = "neta-resume"
    max_s3_workers: int = 4
    s3_part_upload_size: int = 16 * 1024 * 1024

    data_folder: str = "data"
    all_members_file_key: str = "all_lok_sabha_members"

    gcloud_parent_str: str = "projects/neta-resume/locations/asia-south-1"

    model_config = SettingsConfigDict(env_file=".env")


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore
