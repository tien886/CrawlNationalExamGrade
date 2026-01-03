from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Any
import pandas as pd


SUBJECT_COLUMNS = [
    "Toan",
    "Ly",
    "Hoa",
    "Sinh",
    "Van",
    "Su",
    "Dia",
    "NgoaiNgu",
    "GDCD",
]


def safe_sheet_name(name: str) -> str:
    invalid = ['[', ']', ':', '*', '?', '/', '\\']
    for ch in invalid:
        name = name.replace(ch, "")
    name = name.strip()
    return name[:31] if name else "Sheet"


@dataclass
class ExcelExporter:
    filename: str = "national_exam_2024.xlsx"

    def export(self, province_to_rows: Dict[str, List[dict]]) -> str:
        """
        province_to_rows:
          {
            "Sở GD&ĐT Tỉnh Quảng Ngãi": [
              {"candidateNumber": "...", "fullName": "...", "Toan": 7.8, ...},
              ...
            ],
            ...
          }
        """
        cols = ["candidateNumber", "fullName"] + SUBJECT_COLUMNS

        with pd.ExcelWriter(self.filename, engine="openpyxl") as writer:
            for province_name, rows in province_to_rows.items():
                sheet = safe_sheet_name(province_name)

                if rows:
                    df = pd.DataFrame(rows)
                    # ensure all columns exist + ordering
                    for c in cols:
                        if c not in df.columns:
                            df[c] = "X"
                    df = df[cols]
                else:
                    df = pd.DataFrame(columns=cols)

                df.to_excel(writer, sheet_name=sheet, index=False)

        return self.filename
