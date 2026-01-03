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
# How many student IDs to schedule at once (bigger = faster, but more memory)
BATCH_SIZE = 1000
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
async def fetch_student(session: aiohttp.ClientSession, sbd: str) -> Optional[dict]:
    data = await fetch_json(session, build_url(sbd))
    if not is_valid_student(data):
        return None
    return data["data"]["data"]
async def find_provinces(session: aiohttp.ClientSession) -> List[Tuple[int, str]]:
    provinces: List[Tuple[int, str]] = []

    for pid in tqdm(range(1, 65), desc="Detecting provinces"):
        sbd = f"{pid:02d}000001"
        data = await fetch_json(session, build_url(sbd))
        if is_valid_student(data):
            provinces.append((pid, data["data"]["data"]["examCluster"]))

    return provinces


async def find_max_student_id(session: aiohttp.ClientSession, province_id: int) -> int:
    lo, hi = LOW_ID, HIGH_ID
    last_valid = 0

    while lo <= hi:
        mid = (lo + hi) // 2
        sbd = f"{province_id:02d}{mid:06d}"
        data = await fetch_json(session, build_url(sbd))

        if is_valid_student(data):
            last_valid = mid
            lo = mid + 1
        else:
            hi = mid - 1

    return last_valid


# semaphore usage senario, create 1000 requested tasks  at a time 
# then wait for 100 to finish before let the 101th start

async def collect_students_in_province(
    session: aiohttp.ClientSession,
    province_id: int,
    max_student_id: int,
    batch_size: int = BATCH_SIZE,
) -> List[dict]:
    """
    True async concurrency:
    - schedule batch_size requests at once
    - semaphore enforces MAX_CONCURRENCY
    """
    rows: List[dict] = []

    pbar = tqdm(total=max_student_id, desc=f"Province {province_id:02d}", leave=False)

    sid = 1
    while sid <= max_student_id:
        end = min(sid + batch_size - 1, max_student_id)
        tasks = [
            fetch_student(session, f"{province_id:02d}{cur:06d}")
            for cur in range(sid, end + 1)
        ]

        results = await asyncio.gather(*tasks)

        for student_data in results:
            if student_data:
                rows.append(extract_student_row(student_data))

        pbar.update(end - sid + 1)
        sid = end + 1

    pbar.close()
    return rows
async def main():
    exporter = ExcelExporter(filename=f"national_exam_{YEAR}.xlsx")
    province_to_rows: Dict[str, List[dict]] = {}

    timeout = aiohttp.ClientTimeout(total=TIMEOUT_TOTAL)

    # TCPConnector improves performance (connection reuse + limits)
    connector = aiohttp.TCPConnector(
        limit=MAX_CONCURRENCY,          # total open connections
        limit_per_host=MAX_CONCURRENCY, # per host
        ttl_dns_cache=300,
        enable_cleanup_closed=True,
    )

    async with aiohttp.ClientSession(headers=HEADERS, timeout=timeout, connector=connector) as session:
        provinces = await find_provinces(session)

        print("\nDetected provinces:")
        for pid, name in provinces:
            print(f"{pid:02d} → {name}")

        for pid, name in tqdm(provinces, desc="Processing provinces"):
            max_sid = await find_max_student_id(session, pid)
            print(f"{name}: max student_id = {max_sid}")

            rows = await collect_students_in_province(session, pid, max_sid)
            province_to_rows[name] = rows

    out = exporter.export(province_to_rows)
    print(f"\nExcel saved: {out}")


if __name__ == "__main__":
    asyncio.run(main())
