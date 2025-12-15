import os
import time
import requests
from typing import List

# Environment variables for Azure Vision
# VISION_ENDPOINT="https://<your-vision>.cognitiveservices.azure.com/"
# VISION_KEY="your-vision-key"
VISION_ENDPOINT = os.getenv("VISION_ENDPOINT")
VISION_KEY = os.getenv("VISION_KEY")

if not VISION_ENDPOINT or not VISION_KEY:
    raise RuntimeError("VISION_ENDPOINT or VISION_KEY missing in environment variables.")


def _poll_read_result(operation_url: str, retries: int = 10, delay: float = 1.0) -> List[str]:
    """Polls the Read operation and returns extracted lines when succeeded."""
    headers = {"Ocp-Apim-Subscription-Key": VISION_KEY}
    for _ in range(retries):
        resp = requests.get(operation_url, headers=headers, timeout=10)
        resp.raise_for_status()
        body = resp.json()
        status = body.get("status")
        if status == "succeeded":
            lines = []
            analyze_result = body.get("analyzeResult", {})
            for read_result in analyze_result.get("readResults", []):
                for line in read_result.get("lines", []):
                    text = line.get("text")
                    if text:
                        lines.append(text)
            return lines
        if status in {"failed", "cancelled"}:
            raise RuntimeError(f"Vision OCR failed with status={status}")
        time.sleep(delay)
    raise RuntimeError("Vision OCR polling timed out")


def extract_text_from_image_url(image_url: str) -> str:
    """Calls Azure Read API (v3.2) with an image URL and returns extracted text."""
    try:
        endpoint = VISION_ENDPOINT.rstrip("/")
        url = f"{endpoint}/vision/v3.2/read/analyze"
        headers = {
            "Ocp-Apim-Subscription-Key": VISION_KEY,
            "Content-Type": "application/json",
        }
        payload = {"url": image_url}

        submit = requests.post(url, headers=headers, json=payload, timeout=10)
        submit.raise_for_status()
        operation_url = submit.headers.get("Operation-Location")
        if not operation_url:
            raise RuntimeError("Missing Operation-Location header from Vision service.")

        lines = _poll_read_result(operation_url)
        text = "\n".join(lines).strip()
        if not text:
            raise RuntimeError("No text extracted.")
        return text
    except Exception as exc:
        raise RuntimeError(f"Vision OCR error: {exc}") from exc
