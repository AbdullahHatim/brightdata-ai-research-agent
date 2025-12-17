from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urlencode

import requests
from tenacity import retry, stop_after_attempt, wait_exponential


class BrightDataError(RuntimeError):
    pass


class BrightDataClient:
    """Minimal Bright Data client for:
    - SERP API via /request
    - Web Scraper API via /datasets/v3/*
    - Web Archive API via /webarchive/*
    """

    def __init__(self, api_key: str, timeout_s: int = 90) -> None:
        if not api_key:
            raise BrightDataError("Missing BRIGHTDATA_API_KEY.")
        self.api_key = api_key
        self.timeout_s = timeout_s
        self.base = "https://api.brightdata.com"

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    @retry(wait=wait_exponential(min=1, max=20), stop=stop_after_attempt(3))
    def serp_request(
        self,
        *,
        zone: str,
        target_url: str,
        country: Optional[str] = None,
        fmt: str = "json",
        method: str = "GET",
        data_format: Optional[str] = None,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> Any:
        """Calls Bright Data SERP API via POST /request."""
        if not zone:
            raise BrightDataError("Missing BRIGHTDATA_SERP_ZONE (zone).")
        payload: Dict[str, Any] = {
            "zone": zone,
            "url": target_url,
            "format": fmt,
            "method": method,
        }
        if country:
            payload["country"] = country
        if data_format:
            payload["data_format"] = data_format
        if extra_headers:
            payload["headers"] = extra_headers

        r = requests.post(
            f"{self.base}/request",
            headers=self._headers(),
            json=payload,
            timeout=self.timeout_s,
        )
        if r.status_code >= 400:
            raise BrightDataError(f"SERP /request error {r.status_code}: {r.text[:500]}")
        # Try json, fallback to text
        try:
            data = r.json()
            # Handle Web Unlocker / specific SERP modes that wrap the response in {"body": "..."}
            if isinstance(data, dict) and "body" in data and isinstance(data["body"], str):
                try:
                    # Attempt to parse the inner body
                    inner = json.loads(data["body"])
                    return inner
                except Exception:
                    # If parsing fails, just return the data as-is
                    pass
            return data
        except Exception:
            return r.text

    @retry(wait=wait_exponential(min=1, max=20), stop=stop_after_attempt(3))
    def datasets_scrape(
        self,
        *,
        dataset_id: str,
        inputs: List[Dict[str, Any]],
        fmt: str = "json",
        include_errors: bool = True,
        custom_output_fields: Optional[str] = None,
    ) -> Tuple[int, Any]:
        """Synchronous Web Scraper API call. May return 202 with snapshot_id."""
        if not dataset_id:
            raise BrightDataError("Missing dataset_id for /datasets/v3/scrape.")
        params = {"dataset_id": dataset_id, "format": fmt}
        if include_errors:
            params["include_errors"] = "true"
        if custom_output_fields:
            params["custom_output_fields"] = custom_output_fields

        url = f"{self.base}/datasets/v3/scrape?{urlencode(params)}"
        r = requests.post(url, headers=self._headers(), json=inputs, timeout=self.timeout_s)
        # 200: data; 202: snapshot_id
        if r.status_code not in (200, 202):
            raise BrightDataError(f"datasets scrape error {r.status_code}: {r.text[:500]}")
        try:
            return r.status_code, r.json()
        except Exception:
            return r.status_code, r.text

    @retry(wait=wait_exponential(min=1, max=20), stop=stop_after_attempt(3))
    def datasets_trigger(
        self,
        *,
        dataset_id: str,
        inputs: List[Dict[str, Any]],
        fmt: str = "json",
        include_errors: bool = True,
        custom_output_fields: Optional[str] = None,
    ) -> str:
        """Asynchronous Web Scraper API call. Returns snapshot_id."""
        if not dataset_id:
            raise BrightDataError("Missing dataset_id for /datasets/v3/trigger.")
        params = {"dataset_id": dataset_id, "format": fmt}
        if include_errors:
            params["include_errors"] = "true"
        if custom_output_fields:
            params["custom_output_fields"] = custom_output_fields

        url = f"{self.base}/datasets/v3/trigger?{urlencode(params)}"
        r = requests.post(url, headers=self._headers(), json=inputs, timeout=self.timeout_s)
        if r.status_code >= 400:
            raise BrightDataError(f"datasets trigger error {r.status_code}: {r.text[:500]}")
        data = r.json()
        sid = data.get("snapshot_id") or data.get("id")
        if not sid:
            raise BrightDataError(f"Unexpected trigger response: {data}")
        return sid

    @retry(wait=wait_exponential(min=1, max=20), stop=stop_after_attempt(3))
    def datasets_progress(self, snapshot_id: str) -> Dict[str, Any]:
        if not snapshot_id:
            raise BrightDataError("Missing snapshot_id.")
        r = requests.get(
            f"{self.base}/datasets/v3/progress/{snapshot_id}",
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=self.timeout_s,
        )
        if r.status_code >= 400:
            raise BrightDataError(f"progress error {r.status_code}: {r.text[:500]}")
        return r.json()

    @retry(wait=wait_exponential(min=1, max=20), stop=stop_after_attempt(3))
    def datasets_snapshot(self, snapshot_id: str, fmt: str = "json", compress: bool = False) -> Any:
        if not snapshot_id:
            raise BrightDataError("Missing snapshot_id.")
        params = {"format": fmt, "compress": "true" if compress else "false"}
        url = f"{self.base}/datasets/v3/snapshot/{snapshot_id}?{urlencode(params)}"
        r = requests.get(url, headers={"Authorization": f"Bearer {self.api_key}"}, timeout=self.timeout_s)
        if r.status_code >= 400:
            raise BrightDataError(f"snapshot download error {r.status_code}: {r.text[:500]}")
        # The API can return JSON data or 'status building' messages as JSON.
        try:
            return r.json()
        except Exception:
            return r.text

    @retry(wait=wait_exponential(min=1, max=20), stop=stop_after_attempt(3))
    def datasets_list(self) -> List[Dict[str, Any]]:
        r = requests.get(
            f"{self.base}/datasets/list",
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=self.timeout_s,
        )
        if r.status_code >= 400:
            raise BrightDataError(f"datasets list error {r.status_code}: {r.text[:500]}")
        data = r.json()
        if isinstance(data, list):
            return data
        raise BrightDataError(f"Unexpected datasets list response: {data}")

    @retry(wait=wait_exponential(min=1, max=20), stop=stop_after_attempt(3))
    def webarchive_search(self, filters: Dict[str, Any]) -> str:
        r = requests.post(
            f"{self.base}/webarchive/search",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={"filters": filters},
            timeout=self.timeout_s,
        )
        if r.status_code >= 400:
            raise BrightDataError(f"webarchive search error {r.status_code}: {r.text[:500]}")
        data = r.json()
        sid = data.get("search_id")
        if not sid:
            raise BrightDataError(f"Unexpected webarchive search response: {data}")
        return sid

    @retry(wait=wait_exponential(min=1, max=20), stop=stop_after_attempt(3))
    def webarchive_search_status(self, search_id: str) -> Dict[str, Any]:
        r = requests.get(
            f"{self.base}/webarchive/search/{search_id}",
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=self.timeout_s,
        )
        if r.status_code >= 400:
            raise BrightDataError(f"webarchive status error {r.status_code}: {r.text[:500]}")
        return r.json()
