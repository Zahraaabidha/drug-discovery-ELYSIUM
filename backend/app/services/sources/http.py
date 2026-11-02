"""Shared HTTP session with retries, timeouts and an identifying User-Agent."""
from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

log = logging.getLogger(__name__)

DEFAULT_TIMEOUT = float(os.getenv("EXTERNAL_API_TIMEOUT", "40"))


class ExternalServiceError(RuntimeError):
    """An external database could not be reached or returned an unusable response."""

    def __init__(self, service: str, message: str):
        super().__init__(f"{service}: {message}")
        self.service = service


def _session() -> requests.Session:
    s = requests.Session()
    retry = Retry(total=3, backoff_factor=1.0, status_forcelist=(429, 500, 502, 503, 504),
                  allowed_methods=("GET",), respect_retry_after_header=True)
    s.mount("https://", HTTPAdapter(max_retries=retry))
    contact = os.getenv("CONTACT_EMAIL", "")
    s.headers["User-Agent"] = f"ELYSIUM-research/0.2 ({contact})" if contact else "ELYSIUM-research/0.2"
    s.headers["Accept"] = "application/json"
    return s


_SESSION = _session()


def get_json(service: str, url: str, params: Optional[Dict[str, Any]] = None, timeout: Optional[float] = None) -> Any:
    t0 = time.time()
    try:
        r = _SESSION.get(url, params=params, timeout=timeout or DEFAULT_TIMEOUT)
    except requests.RequestException as exc:
        raise ExternalServiceError(service, f"request failed ({exc.__class__.__name__}: {exc})") from exc
    log.info("%s GET %s -> %s (%.2fs)", service, r.url, r.status_code, time.time() - t0)
    if r.status_code == 404:
        return None
    if not r.ok:
        raise ExternalServiceError(service, f"HTTP {r.status_code} for {r.url}")
    if not r.content.strip():
        raise ExternalServiceError(service, f"empty response body from {r.url} (service degraded or rate-limiting)")
    try:
        return r.json()
    except ValueError as exc:
        raise ExternalServiceError(service, "response was not valid JSON") from exc
