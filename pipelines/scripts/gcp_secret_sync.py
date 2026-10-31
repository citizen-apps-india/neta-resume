from pathlib import Path

from dotenv import dotenv_values
from google.api_core.exceptions import AlreadyExists, NotFound
from google.cloud.secretmanager_v1 import SecretManagerServiceAsyncClient
from google.cloud.secretmanager_v1.types import Replication, Secret, SecretPayload
from settings import Settings, _is_secret


class GCPSecretSync:
    def __init__(self) -> None:
        self._settings_class = Settings
        self._secret_path_base = "projects/neta-resume/secrets"
        # Read the .env file here on initialization
        self._loaded_env = dotenv_values(Path(__file__).parent.parent / ".env")

    async def upsert_secret(
        self,
        secret_name: str,
        secret_value: str,
        _client: SecretManagerServiceAsyncClient,
    ):
        try:
            response = await _client.access_secret_version(
                name=f"{self._secret_path_base}/{secret_name}/versions/latest"
            )
            if response.payload.data == secret_value.encode():
                return

        except NotFound:
            try:
                await _client.create_secret(
                    parent="projects/neta-resume",
                    secret_id=secret_name,
                    secret=Secret(
                        replication=Replication(
                            user_managed=Replication.UserManaged(
                                replicas=[
                                    Replication.UserManaged.Replica(
                                        location="asia-south1"
                                    )
                                ]
                            )
                        )
                    ),
                )
            except AlreadyExists:
                pass

        await _client.add_secret_version(
            parent=f"projects/neta-resume/secrets/{secret_name}",
            payload=SecretPayload(data=secret_value.encode()),
        )

    async def sync_local_secrets_to_gcp(self):
        async with SecretManagerServiceAsyncClient() as _client:
            for field_name, field_info in self._settings_class.model_fields.items():
                if _is_secret(field=field_info):
                    # Get it from the local env file and upsert to google secret manager
                    value = self._loaded_env.get(field_name.upper(), None)
                    if value and value != "":
                        await self.upsert_secret(field_name, value, _client)
