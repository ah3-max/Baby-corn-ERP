"""
WP2：QC 品質管理強化 — Pydantic Schemas
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Any
from uuid import UUID
from pydantic import BaseModel


# ── QCSamplingRule ────────────────────────────────────────

class QCSamplingRuleCreate(BaseModel):
    rule_code:         str
    product_type_id:   Optional[str] = None
    batch_size_min_kg: Optional[Decimal] = None
    batch_size_max_kg: Optional[Decimal] = None
    sampling_pct:      Decimal
    boxes_per_sample:  int = 1
    description:       Optional[str] = None

class QCSamplingRuleUpdate(BaseModel):
    batch_size_min_kg: Optional[Decimal] = None
    batch_size_max_kg: Optional[Decimal] = None
    sampling_pct:      Optional[Decimal] = None
    boxes_per_sample:  Optional[int] = None
    description:       Optional[str] = None
    is_active:         Optional[bool] = None

class QCSamplingRuleOut(BaseModel):
    id:                str
    rule_code:         str
    product_type_id:   Optional[str]
    batch_size_min_kg: Optional[float]
    batch_size_max_kg: Optional[float]
    sampling_pct:      float
    boxes_per_sample:  int
    description:       Optional[str]
    is_active:         bool
    created_at:        datetime
    class Config: from_attributes = True


# ── QCScoreCard ──────────────────────────────────────────

class QCScoreCardCreate(BaseModel):
    score_item:  str
    score_value: Optional[Decimal] = None
    score_text:  Optional[str] = None
    is_pass:     Optional[bool] = None
    weight:      Decimal = Decimal("1")
    note:        Optional[str] = None

class QCScoreCardOut(BaseModel):
    id:          str
    score_item:  str
    score_value: Optional[float]
    score_text:  Optional[str]
    is_pass:     Optional[bool]
    weight:      float
    ai_score:    Optional[Any]
    note:        Optional[str]
    created_at:  datetime
    class Config: from_attributes = True


# ── QCPhoto ──────────────────────────────────────────────

class QCPhotoOut(BaseModel):
    id:            str
    photo_type:    str
    file_url:      str
    thumbnail_url: Optional[str]
    box_no:        Optional[str]
    unit_no:       Optional[str]
    caption:       Optional[str]
    ai_analysis:   Optional[Any]
    created_at:    datetime
    class Config: from_attributes = True


# ── QCInspection ─────────────────────────────────────────

class QCInspectionCreate(BaseModel):
    batch_id:                str
    inspection_stage:        str
    sampling_rule_id:        Optional[str] = None
    total_boxes_in_batch:    Optional[int] = None
    sampled_boxes:           Optional[int] = None
    sampled_units:           Optional[int] = None
    inspector_name:          str
    inspection_datetime:     Optional[datetime] = None
    environment_temp_c:      Optional[Decimal] = None
    environment_humidity_pct: Optional[Decimal] = None
    overall_result:          str  # pass / fail / conditional_pass
    overall_grade:           Optional[str] = None
    overall_score:           Optional[Decimal] = None
    defect_summary:          Optional[dict] = None
    grade_distribution:      Optional[dict] = None
    recommendation:          Optional[str] = None
    next_batch_notes:        Optional[str] = None
    pesticide_test_result:   Optional[list] = None
    # 內嵌評分卡
    score_cards:             Optional[List[QCScoreCardCreate]] = None

class QCInspectionUpdate(BaseModel):
    overall_result:          Optional[str] = None
    overall_grade:           Optional[str] = None
    overall_score:           Optional[Decimal] = None
    defect_summary:          Optional[dict] = None
    grade_distribution:      Optional[dict] = None
    recommendation:          Optional[str] = None
    next_batch_notes:        Optional[str] = None
    pesticide_test_result:   Optional[list] = None

class QCInspectionOut(BaseModel):
    id:                      str
    inspection_no:           str
    batch_id:                str
    inspection_stage:        str
    sampling_rule_id:        Optional[str]
    total_boxes_in_batch:    Optional[int]
    sampled_boxes:           Optional[int]
    sampled_units:           Optional[int]
    inspector_user_id:       Optional[str]
    inspector_name:          str
    inspection_datetime:     datetime
    environment_temp_c:      Optional[float]
    environment_humidity_pct: Optional[float]
    overall_result:          str
    overall_grade:           Optional[str]
    overall_score:           Optional[float]
    defect_summary:          Optional[Any]
    grade_distribution:      Optional[Any]
    recommendation:          Optional[str]
    next_batch_notes:        Optional[str]
    pesticide_test_result:   Optional[Any]
    created_at:              datetime
    updated_at:              Optional[datetime]
    photos:                  List[QCPhotoOut] = []
    score_cards:             List[QCScoreCardOut] = []
    class Config: from_attributes = True


# ── ChannelQCStandard ────────────────────────────────────

class ChannelQCStandardCreate(BaseModel):
    standard_code:      str
    channel_type:       str
    customer_id:        Optional[str] = None
    product_type_id:    Optional[str] = None
    grade_requirements: Optional[dict] = None
    pricing_tier:       Optional[dict] = None
    description:        Optional[str] = None

class ChannelQCStandardUpdate(BaseModel):
    channel_type:       Optional[str] = None
    grade_requirements: Optional[dict] = None
    pricing_tier:       Optional[dict] = None
    description:        Optional[str] = None
    is_active:          Optional[bool] = None

class ChannelQCStandardOut(BaseModel):
    id:                 str
    standard_code:      str
    channel_type:       str
    customer_id:        Optional[str]
    product_type_id:    Optional[str]
    grade_requirements: Optional[Any]
    pricing_tier:       Optional[Any]
    description:        Optional[str]
    is_active:          bool
    created_at:         datetime
    class Config: from_attributes = True


# ── ProcessingStepLog ────────────────────────────────────

class ProcessingStepLogCreate(BaseModel):
    batch_id:              str
    step_name:             str
    step_sequence:         int = 0
    started_at:            Optional[datetime] = None
    completed_at:          Optional[datetime] = None
    operator_name:         Optional[str] = None
    environment_temp_c:    Optional[Decimal] = None
    environment_humidity_pct: Optional[Decimal] = None
    input_weight_kg:       Optional[Decimal] = None
    output_weight_kg:      Optional[Decimal] = None
    waste_kg:              Optional[Decimal] = None
    notes:                 Optional[str] = None
    photos:                Optional[list] = None

class ProcessingStepLogOut(BaseModel):
    id:                    str
    processing_order_id:   str
    batch_id:              str
    step_name:             str
    step_sequence:         int
    started_at:            Optional[datetime]
    completed_at:          Optional[datetime]
    operator_name:         Optional[str]
    environment_temp_c:    Optional[float]
    environment_humidity_pct: Optional[float]
    input_weight_kg:       Optional[float]
    output_weight_kg:      Optional[float]
    waste_kg:              Optional[float]
    notes:                 Optional[str]
    photos:                Optional[Any]
    created_at:            datetime
    class Config: from_attributes = True


# ── TemperatureLog ───────────────────────────────────────

class TemperatureLogCreate(BaseModel):
    entity_type:          str
    entity_id:            str
    log_source:           str = "manual"
    sensor_id:            Optional[str] = None
    temperature_c:        Decimal
    humidity_pct:         Optional[Decimal] = None
    location_description: Optional[str] = None
    is_alert:             bool = False
    alert_reason:         Optional[str] = None
    recorded_at:          Optional[datetime] = None

class TemperatureLogOut(BaseModel):
    id:                   str
    entity_type:          str
    entity_id:            str
    log_source:           str
    sensor_id:            Optional[str]
    temperature_c:        float
    humidity_pct:         Optional[float]
    location_description: Optional[str]
    is_alert:             bool
    alert_reason:         Optional[str]
    recorded_at:          datetime
    created_at:           datetime
    class Config: from_attributes = True
