import asyncio
import aiohttp
from typing import Optional, Dict, List, Tuple
from exporter import ExcelExporter, SUBJECT_COLUMNS
from tqdm import tqdm  # <-- use normal tqdm for loops
# ================= CONFIG =================

BASE_DOMAIN = "https://vietnamnet.vn/newsapi-edu/EducationStudentScore/CheckCandidateNumber"
COMPONENT_ID = "ComponentId=COMPONENT002298"
PAGE_ID = "PageId=fa4119c27edb45558886cde08459bb1b"
YEAR = "2024"
TYPE = "type=2"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
}

MAX_CONCURRENCY = 100        # keep low to avoid rate-limit/bans
TIMEOUT_TOTAL = 10         # seconds (per request)
LOW_ID = 1
HIGH_ID = 150_000

def build_url(sbd: str) -> str:
    return (
        f"{BASE_DOMAIN}?"
        f"{COMPONENT_ID}&{PAGE_ID}"
        f"&sbd={sbd}&{TYPE}&year={YEAR}"
    )
sem = asyncio.Semaphore(MAX_CONCURRENCY)
async def fetch_json(session: aiohttp.ClientSession, url: str, retries: int = 2) -> Optional[dict]:
    """
    Robust fetch:
    - semaphore limits concurrency
    - retries transient failures
    - content_type=None handles wrong/missing Content-Type
    """
    for attempt in range(retries + 1):
        async with sem:
            try:
                async with session.get(url) as r:
                    # sometimes servers return JSON with wrong header; allow it
                    return await r.json(content_type=None)
            except Exception:
                if attempt == retries:
                    return None
                await asyncio.sleep(0.2 * (attempt + 1))  # tiny backoff
def is_valid_student(resp: Optional[dict]) -> bool:
    if not resp:
        return False
    # business check: model is False/None when not found
    return resp.get("data", {}).get("model") not in (False, None)

def extract_student_row(student_data: dict) -> dict:
    row = {
        "candidateNumber": student_data.get("candidateNumber"),
        "fullName": student_data.get("fullName", "") or "",
    }

    subject_scores = student_data.get("subjectScores", {}) or {}
    for subject in SUBJECT_COLUMNS:
        row[subject] = subject_scores.get(subject, {}).get("point", "X") if subject in subject_scores else "X"

    return row
