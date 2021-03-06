import pickle
import tarfile
import logging

from typing import Any
from awswrangler.exceptions import InvalidParameters

logger = logging.getLogger(__name__)


class SageMaker:
    def __init__(self, session):
        self._session = session
        self._client_s3 = session.boto3_session.client(service_name="s3", use_ssl=True, config=session.botocore_config)
        self._client_sagemaker = session.boto3_session.client(service_name="sagemaker")

    @staticmethod
    def _parse_path(path):
        path2 = path.replace("s3://", "")
        parts = path2.partition("/")
        return parts[0], parts[2]

    def get_job_outputs(self, job_name: str = None, path: str = None) -> Any:

        if path and job_name:
            raise InvalidParameters("Specify either path, job_arn or job_name")

        if job_name:
            path = self._client_sagemaker.describe_training_job(
                TrainingJobName=job_name)["ModelArtifacts"]["S3ModelArtifacts"]

        if not self._session.s3.does_object_exists(path):
            return None

        bucket, key = SageMaker._parse_path(path)
        if key.split("/")[-1] != "model.tar.gz":
            key = f"{key}/model.tar.gz"

        body = self._client_s3.get_object(Bucket=bucket, Key=key)["Body"].read()
        body = tarfile.io.BytesIO(body)  # type: ignore
        tar = tarfile.open(fileobj=body)

        results = []
        for member in tar.getmembers():
            f = tar.extractfile(member)
            file_type = member.name.split(".")[-1]

            if (file_type == "pkl") and (f is not None):
                f = pickle.load(f)

            results.append(f)

        return results
