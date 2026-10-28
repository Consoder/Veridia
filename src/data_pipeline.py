"""
Data Ingestion, Sanitation, and Validation Pipeline for Veridia
Handles noisy inputs, duplicate IDs, out-of-bound percentages, and missing values.
"""
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime, date
import logging
import pandas as pd
import numpy as np

from src.config import RAW_DATA_PATH, SANITIZED_DATA_PATH, DEFAULT_AS_OF_DATE
from src.models import CleanedManufacturer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

class DataPipeline:
    """Robust data processing pipeline with audit logging and sanity enforcement."""

    def __init__(self, raw_csv_path: Path = RAW_DATA_PATH):
        self.raw_csv_path = Path(raw_csv_path)
        self._cleaned_manufacturers: Optional[List[CleanedManufacturer]] = None

    def load_and_sanitize(self, force_refresh: bool = False) -> List[CleanedManufacturer]:
        """Loads raw CSV, applies rigorous sanitation, and returns typed Pydantic models."""
        if self._cleaned_manufacturers is not None and not force_refresh:
            return self._cleaned_manufacturers

        if not self.raw_csv_path.exists():
            raise FileNotFoundError(f"Source dataset not found at: {self.raw_csv_path}")

        logger.info(f"Ingesting raw dataset from: {self.raw_csv_path}")
        df = pd.read_csv(self.raw_csv_path)
        total_rows = len(df)
        logger.info(f"Loaded {total_rows} raw manufacturer records.")

        # Compute median lead times by primary process for intelligent imputation
        valid_lead_times = df.dropna(subset=['lead_time_weeks'])
        median_lead_by_process = valid_lead_times.groupby('primary_process')['lead_time_weeks'].median().to_dict()
        global_median_lead_weeks = float(valid_lead_times['lead_time_weeks'].median())

        cleaned_records: List[CleanedManufacturer] = []
        id_counter: Dict[str, int] = {}

        # First pass to identify duplicates
        raw_id_counts = df['manufacturer_id'].value_counts().to_dict()

        for idx, row in df.iterrows():
            flags: List[str] = []
            raw_id = str(row['manufacturer_id']).strip()

            # 1. Handle Duplicate Manufacturer IDs
            if raw_id_counts.get(raw_id, 0) > 1:
                instance_idx = id_counter.get(raw_id, 1)
                surrogate_id = f"{raw_id}-FACILITY-{instance_idx}"
                id_counter[raw_id] = instance_idx + 1
                flags.append(f"DUPLICATE_ID_RESOLVED (Facility #{instance_idx})")
            else:
                surrogate_id = raw_id

            # 2. Handle Physically Impossible On-Time Delivery (> 100%)
            raw_otd = float(row['on_time_delivery_pct']) if pd.notnull(row['on_time_delivery_pct']) else 85.0
            if raw_otd > 100.0:
                flags.append(f"OTD_CLAMPED (Raw: {raw_otd:.1f}% -> Clamped: 100.0%)")
                clamped_otd = 100.0
            elif raw_otd < 0.0:
                flags.append(f"OTD_NEGATIVE (Raw: {raw_otd:.1f}% -> Clamped: 0.0%)")
                clamped_otd = 0.0
            else:
                clamped_otd = raw_otd

            # 3. Handle Missing Lead Times (NaN)
            lead_weeks = row['lead_time_weeks']
            primary_proc = str(row['primary_process']).strip()
            if pd.isnull(lead_weeks) or lead_weeks <= 0:
                imputed_weeks = float(median_lead_by_process.get(primary_proc, global_median_lead_weeks))
                lead_weeks = imputed_weeks
                lead_days = imputed_weeks * 7.0
                flags.append(f"LEAD_TIME_IMPUTED (Process median: {imputed_weeks:.1f} weeks)")
            else:
                lead_weeks = float(lead_weeks)
                lead_days = float(row['lead_time_days']) if pd.notnull(row['lead_time_days']) else lead_weeks * 7.0

            # 4. Parse Dates
            try:
                cert_expiry = datetime.strptime(str(row['certification_expiry']).strip(), "%Y-%m-%d").date()
            except Exception:
                cert_expiry = date(2027, 1, 1)
                flags.append("CORRUPTED_EXPIRY_DATE_NORMALIZED")

            try:
                last_audit = datetime.strptime(str(row['last_audit_date']).strip(), "%Y-%m-%d").date()
            except Exception:
                last_audit = date(2025, 1, 1)
                flags.append("CORRUPTED_AUDIT_DATE_NORMALIZED")

            # 5. Tokenize Delimited Fields
            def parse_delimited(val: Any) -> List[str]:
                if pd.isnull(val):
                    return []
                return [item.strip() for item in str(val).split(';') if item.strip()]

            processes = parse_delimited(row['processes'])
            materials = parse_delimited(row['materials'])
            certifications = parse_delimited(row['certifications'])

            # 6. Numeric Constraints & Sanity Checks
            min_oq = int(row['min_order_qty']) if pd.notnull(row['min_order_qty']) else 100
            max_oq = int(row['max_order_qty']) if pd.notnull(row['max_order_qty']) else 5000
            if min_oq > max_oq:
                min_oq, max_oq = max_oq, min_oq
                flags.append("INVERTED_ORDER_QUANTITY_SWAPPED")

            # Assemble typed record
            cleaned_mfg = CleanedManufacturer(
                manufacturer_id=surrogate_id,
                raw_id=raw_id,
                name=str(row['name']).strip(),
                country=str(row.get('country', 'India')).strip(),
                city=str(row['city']).strip(),
                state=str(row['state']).strip(),
                state_name=str(row['state_name']).strip(),
                full_address=str(row['full_address']).strip(),
                contact_email=str(row['contact_email']).strip(),
                website=str(row['website']).strip(),
                founded_year=int(row['founded_year']),
                employee_count=int(row['employee_count']),
                company_size=str(row['company_size']).strip(),
                capacity_units_per_month=int(row['capacity_units_per_month']),
                capacity_tier=str(row['capacity_tier']).strip(),
                processes=processes,
                primary_process=primary_proc,
                process_count=len(processes),
                materials=materials,
                certifications=certifications,
                certification_count=len(certifications),
                certification_expiry=cert_expiry,
                last_audit_date=last_audit,
                min_order_qty=min_oq,
                max_order_qty=max_oq,
                order_range=f"{min_oq}-{max_oq}",
                lead_time_weeks=round(lead_weeks, 1),
                lead_time_days=round(lead_days, 1),
                export_experience_years=int(row['export_experience_years']),
                on_time_delivery_pct=round(clamped_otd, 1),
                raw_on_time_delivery_pct=round(raw_otd, 1),
                delivery_rating=str(row['delivery_rating']).strip().upper(),
                status=str(row.get('status', 'active')).strip().lower(),
                data_quality_flags=flags
            )
            cleaned_records.append(cleaned_mfg)

        self._cleaned_manufacturers = cleaned_records
        logger.info(f"Sanitization complete: {len(cleaned_records)} verified records ready.")
        return cleaned_records

    def export_sanitized_csv(self, output_path: Path = SANITIZED_DATA_PATH) -> Path:
        """Saves sanitized dataset to disk for external consumption & audit inspection."""
        manufacturers = self.load_and_sanitize()
        data_dicts = []
        for m in manufacturers:
            d = m.model_dump()
            d['processes'] = ';'.join(d['processes'])
            d['materials'] = ';'.join(d['materials'])
            d['certifications'] = ';'.join(d['certifications'])
            d['data_quality_flags'] = ';'.join(d['data_quality_flags'])
            data_dicts.append(d)

        out_df = pd.DataFrame(data_dicts)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        out_df.to_csv(output_path, index=False)
        logger.info(f"Exported sanitized dataset to: {output_path}")
        return output_path


# Global instance helper
_pipeline_instance = None

def get_pipeline() -> DataPipeline:
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = DataPipeline()
    return _pipeline_instance
