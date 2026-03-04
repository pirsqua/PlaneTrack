"""Azure Data Lake Gen2 client for Parquet I/O."""

import io
import logging

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from azure.core.exceptions import ResourceNotFoundError
from azure.storage.filedatalake import DataLakeServiceClient

from app.config import Settings

logger = logging.getLogger(__name__)


class ADLSClient:
    def __init__(self, settings: Settings) -> None:
        self._container = settings.adls_container
        self._service = DataLakeServiceClient(
            account_url=f"https://{settings.azure_account_name}.dfs.core.windows.net",
            credential=settings.azure_account_key,
        )
        self._fs = self._service.get_file_system_client(self._container)

    def write_parquet(self, path: str, df: pd.DataFrame) -> None:
        """Write a DataFrame as Parquet to the given ADLS path."""
        buf = io.BytesIO()
        table = pa.Table.from_pandas(df, preserve_index=False)
        pq.write_table(table, buf, compression="snappy")
        buf.seek(0)

        file_client = self._fs.get_file_client(path)
        data = buf.getvalue()
        file_client.upload_data(data, overwrite=True, length=len(data))
        logger.debug("Wrote %d rows (%d bytes) to adls://%s/%s", len(df), len(data), self._container, path)

    def read_parquet(self, path: str) -> pd.DataFrame:
        """Read Parquet from the given ADLS path into a DataFrame."""
        file_client = self._fs.get_file_client(path)
        download = file_client.download_file()
        buf = io.BytesIO(download.readall())
        return pq.read_table(buf).to_pandas()

    def list_paths(self, prefix: str) -> list[str]:
        """Return a sorted list of file paths under the given prefix."""
        try:
            paths = self._fs.get_paths(path=prefix, recursive=True)
            return sorted(p.name for p in paths if not p.is_directory)
        except ResourceNotFoundError:
            return []

    def latest_path(self, prefix: str) -> str | None:
        """Return the lexicographically last file under the prefix (newest partition)."""
        paths = self.list_paths(prefix)
        return paths[-1] if paths else None
