"""
Unit tests for Veridia Data Sanitation and Ingestion Pipeline
"""
import pytest
from pathlib import Path
from src.data_pipeline import DataPipeline, get_pipeline
from src.models import CleanedManufacturer

def test_pipeline_ingestion():
    pipe = get_pipeline()
    records = pipe.load_and_sanitize()
    assert len(records) == 1000
    assert all(isinstance(r, CleanedManufacturer) for r in records)

def test_duplicate_id_resolution():
    pipe = get_pipeline()
    records = pipe.load_and_sanitize()

    # Verify all surrogate IDs are strictly unique
    all_ids = [r.manufacturer_id for r in records]
    assert len(all_ids) == len(set(all_ids)), "Surrogate manufacturer IDs must be strictly unique!"

    # Check known collided raw ID VM1092
    vm1092_facilities = [r for r in records if r.raw_id == "VM1092"]
    assert len(vm1092_facilities) == 2
    assert vm1092_facilities[0].manufacturer_id != vm1092_facilities[1].manufacturer_id
    assert any("DUPLICATE_ID" in f for f in vm1092_facilities[0].data_quality_flags)

def test_otd_percentage_clamping():
    pipe = get_pipeline()
    records = pipe.load_and_sanitize()

    # All clamped on_time_delivery_pct must be <= 100.0%
    assert all(r.on_time_delivery_pct <= 100.0 for r in records)
    assert all(r.on_time_delivery_pct >= 0.0 for r in records)

    # Check known raw outlier VM1429 (raw was 142.6%)
    vm1429 = next(r for r in records if r.raw_id == "VM1429")
    assert vm1429.raw_on_time_delivery_pct == 142.6
    assert vm1429.on_time_delivery_pct == 100.0
    assert any("OTD_CLAMPED" in f for f in vm1429.data_quality_flags)

def test_missing_lead_time_imputation():
    pipe = get_pipeline()
    records = pipe.load_and_sanitize()

    # Ensure no NaN lead times remain
    assert all(r.lead_time_weeks > 0 for r in records)
    assert all(r.lead_time_days > 0 for r in records)

    # Check known NaN record VM1150
    vm1150 = next(r for r in records if r.raw_id == "VM1150")
    assert vm1150.lead_time_weeks == 8.0
    assert vm1150.lead_time_days == 56.0
    assert any("LEAD_TIME_IMPUTED" in f for f in vm1150.data_quality_flags)

def test_export_sanitized_csv(tmp_path):
    pipe = get_pipeline()
    temp_csv = tmp_path / "test_sanitized.csv"
    out = pipe.export_sanitized_csv(temp_csv)
    assert out.exists()
    assert out.stat().st_size > 100000
