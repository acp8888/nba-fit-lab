import duckdb
import boto3


def connect() -> duckdb.DuckDBPyConnection:
    session = boto3.Session(profile_name="nba-fit-lab")
    creds = session.get_credentials().get_frozen_credentials()

    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute(f"""
        CREATE SECRET s3_secret (
            TYPE S3,
            KEY_ID '{creds.access_key}',
            SECRET '{creds.secret_key}',
            REGION 'us-east-1'
        )
    """)
    return con
