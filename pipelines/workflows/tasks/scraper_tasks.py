import datetime

from google.api_core.exceptions import GoogleAPICallError
from google.cloud.run_v2 import Container, Job, UpdateJobRequest
from google.cloud.run_v2.services.jobs.async_client import JobsAsyncClient
from settings import get_settings
from structlog import get_logger


class GoogleTaskExecutor:
    def __init__(self):
        settings = get_settings()
        self._gcloud_parent_str = settings.gcloud_parent_str
        self._settings = settings
        self._logger = get_logger()

    async def upsert_pipeline_job(self):
        async with JobsAsyncClient() as _client:
            job_name = (
                f"{self._gcloud_parent_str}/jobs/{self._settings.gcloud_job_name}"
            )
            job = Job(name=job_name)
            job.template.template.max_retries = 5
            job.template.template.timeout = datetime.timedelta(
                minutes=self._settings.gcloud_job_timeout
            )  # type: ignore[assignment]
            job.labels = {
                "application": "neta-resume",
                "managed-by": "neta-resume-admin",
            }
            job.template.template.containers = [
                Container(
                    image=self._settings.gcloud_job_image,
                    args=["scrape-all-sansad-members"],
                )
            ]
            job.template.template.service_account = (
                self._settings.gcloud_service_account
            )
            logger = self._logger.bind(
                job_name=job_name, image=self._settings.gcloud_job_image
            )

            request = UpdateJobRequest(
                job=job,
                allow_missing=True,
            )

            try:
                operation = await _client.update_job(request=request)
                await logger.ainfo(
                    "job upsert starting", operation_name=operation.operation.name
                )
                result = await operation.result()
                await logger.ainfo("job upserted", name=result.name)
            except GoogleAPICallError as exception:
                await logger.aexception(
                    "job upsert failed",
                    error_code=exception.code,
                    message=exception.message,
                    details=exception.details,
                )
                raise
            except Exception:
                await logger.aexception("job upsert failed")
                raise
