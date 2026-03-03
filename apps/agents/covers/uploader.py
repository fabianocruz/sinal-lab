"""Vercel Blob uploader for cover images.

Uploads generated cover images to Vercel Blob via REST API.
Uses httpx for HTTP requests with the shared client factory.

Architecture:
    pipeline.py (orchestrator)
    └── uploader.py  <- this module
        └── httpx.Client  <- shared HTTP layer
"""

import logging
import os
from dataclasses import dataclass
from typing import Optional

import httpx

from apps.agents.sources.http import HttpClientConfig, create_http_client

logger = logging.getLogger(__name__)

BLOB_API_URL = "https://blob.vercel-storage.com"
BLOB_UPLOAD_TIMEOUT = 30.0


@dataclass
class UploadedCover:
    """Result of a successful Vercel Blob upload."""

    url: str
    pathname: str


class BlobUploader:
    """Uploads images to Vercel Blob via REST API.

    Uses PUT with Bearer token authentication. Returns public URL on success,
    None on any failure.
    """

    def __init__(
        self,
        token: Optional[str] = None,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        self._token = token or os.environ.get("BLOB_READ_WRITE_TOKEN", "")
        self._external_client = http_client

    @property
    def is_available(self) -> bool:
        return bool(self._token)

    def upload(
        self,
        image_bytes: bytes,
        filename: str,
        content_type: str = "image/png",
    ) -> Optional[UploadedCover]:
        """Upload an image to Vercel Blob.

        Args:
            image_bytes: Raw image bytes to upload.
            filename: Pathname in the blob store (e.g., covers/radar/ed30-v1.png).
            content_type: MIME type of the image.

        Returns:
            UploadedCover with public URL, or None on failure.
        """
        if not self.is_available:
            logger.warning("Vercel Blob token not set")
            return None

        if not image_bytes:
            logger.warning("Empty image bytes — skipping upload")
            return None

        client = self._get_client()
        try:
            response = client.put(
                f"{BLOB_API_URL}/{filename}",
                content=image_bytes,
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Content-Type": content_type,
                    "x-api-version": "7",
                },
            )
            response.raise_for_status()

            data = response.json()
            return UploadedCover(
                url=data["url"],
                pathname=data.get("pathname", filename),
            )

        except httpx.TimeoutException:
            logger.warning("Vercel Blob upload timeout for %s", filename)
            return None
        except httpx.HTTPStatusError as e:
            logger.warning(
                "Vercel Blob upload error for %s: %d %s",
                filename, e.response.status_code, e.response.text[:200],
            )
            return None
        except (KeyError, ValueError) as e:
            logger.warning("Unexpected Vercel Blob response for %s: %s", filename, e)
            return None
        except Exception as e:
            logger.warning("Vercel Blob unexpected error for %s: %s", filename, e)
            return None
        finally:
            if not self._external_client:
                client.close()

    def _get_client(self) -> httpx.Client:
        """Get or create an httpx client."""
        if self._external_client:
            return self._external_client
        return create_http_client(HttpClientConfig(timeout=BLOB_UPLOAD_TIMEOUT))
