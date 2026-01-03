import asyncio
import aiohttp
from typing import Optional, Dict, List, Tuple

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

MAX_CONCURRENCY = 5        # keep low to avoid rate-limit/bans
TIMEOUT_TOTAL = 10         # seconds (per request)
LOW_ID = 1
HIGH_ID = 150_000
