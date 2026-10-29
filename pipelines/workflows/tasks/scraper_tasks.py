import uuid

import docker
from google.cloud.run_v2 import CreateJobRequest, Job
from google.cloud.run_v2.services.jobs.async_client import JobsAsyncClient
from settings import get_settings


class GoogleTaskExecutor:
    def __init__(self):
        self._client = JobsAsyncClient()
        settings = get_settings()
        self._gcloud_parent_str = settings.gcloud_parent_str

    def create_task_image(self):
        # We will have different executions of jobs
        # but we will have one image and job scheduled for the scrapers.
        client = docker.from_env()
        client.

    async def create_sansad_all_members_fetch_task(self):
        job = Job()
        job.start_execution_token = "upsert_all_sansad_members"
        job.template.template.max_retries = 5

        request = CreateJobRequest(
            parent=self._gcloud_parent_str, job=job, job_id=uuid.uuid4()
        )

        operation = await self._client.create_job(request=request)
        response = operation.result()
        print(response)
