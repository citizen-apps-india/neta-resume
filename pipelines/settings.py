from functools import lru_cache
from typing import Any

from pydantic import SecretStr
from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    GoogleSecretManagerSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


def _is_secret(field) -> bool:
    annotation = field.annotation
    return annotation is SecretStr or SecretStr in getattr(annotation, "__args__", ())


class SecretOnlyGoogleSettingsSource(GoogleSecretManagerSettingsSource):
    def get_field_value(
        self, field: FieldInfo, field_name: str
    ) -> tuple[Any, str, bool]:
        if not _is_secret(field=field):
            return None, field_name, False
        return super().get_field_value(field, field_name)


class Settings(BaseSettings):
    cf_account_id: str = "cb0b4addb47c5dd527a528f38eb07dc8"
    cf_secret_access_key: SecretStr
    cf_account_access_id: str = "623da841dfdf298a99bc8bc6755f696d"

    cf_bucket_name: str = "neta-resume"
    max_s3_workers: int = 4
    s3_part_upload_size: int = 16 * 1024 * 1024

    data_folder: str = "data"
    all_members_file_key: str = "all_lok_sabha_members"

    gcloud_parent_str: str = "projects/neta-resume/locations/asia-south1"
    gcloud_job_image: str
    gcloud_job_name: str = "scrape-job-generic"
    gcloud_job_timeout: int = 20
    gcloud_secret_path: str = "projects/neta-resume/secrets"
    gcloud_service_account: str = (
        "neta-resume-runtime@neta-resume.iam.gserviceaccount.com"
    )

    model_config = SettingsConfigDict(env_file=".env")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        gcp_settings = SecretOnlyGoogleSettingsSource(
            settings_cls, project_id="neta-resume"
        )

        return (
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
            gcp_settings,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore
