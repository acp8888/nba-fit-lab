from datetime import datetime
import json
import hashlib
import boto3
from botocore.exceptions import ClientError
from pathlib import Path


def compute_sha256(file_path: Path) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()


def upload_files(source: str, file_paths: list[Path]) -> None:
    s3 = boto3.Session(profile_name="nba-fit-lab").client("s3")
    bucket = "nba-fit-lab"

    manifest_dir = Path("data/local/raw") / source
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / "manifest.jsonl"

    for file_path in file_paths:
        date_folder = file_path.parent.name  # e.g. "2026-07-12"
        key = f"raw/{source}/{date_folder}/{file_path.name}"
        current_hash = compute_sha256(file_path)

        try:
            response = s3.head_object(Bucket=bucket, Key=key)
            stored_hash = response["Metadata"]["sha256"]

            if stored_hash == current_hash:
                # same file, already uploaded — skip silently, manifest line already exists
                continue
            else:
                raise ValueError(
                    f"Hash mismatch for {key}: raw data should be immutable"
                )
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                with open(file_path, "rb") as f:
                    file_bytes = f.read()
                s3.put_object(
                    Bucket=bucket,
                    Key=key,
                    Body=file_bytes,
                    Metadata={"sha256": current_hash},
                )

                manifest_entry = {
                    "date": date_folder,
                    "filename": file_path.name,
                    "sha256": current_hash,
                    "uploaded_at": datetime.utcnow().isoformat(),
                    "s3_key": key,
                }
                with open(manifest_path, "a") as m:
                    m.write(json.dumps(manifest_entry) + "\n")
            else:
                raise
