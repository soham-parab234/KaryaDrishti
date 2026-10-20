"""Pydantic schemas for CSV ingestion, validation, and batch persistence."""

from pydantic import BaseModel, Field

class RowValidationError(BaseModel):
    row_number: int = Field(..., description="1-indexed row number in the CSV file")
    field: str = Field(..., description="Column or attribute that failed validation")
    error_message: str = Field(..., description="Human-readable explanation of why the row was rejected")
    raw_value: str | None = Field(None, description="The erroneous raw string value provided")

class ValidatedPostingItem(BaseModel):
    posting_id: str
    raw_title: str
    district_code: str
    observation_date: str
    source_system: str
    vacancy_count: int

class ValidationSummaryResponse(BaseModel):
    status: str = Field(..., description="'VALID' if all rows passed, 'INVALID' if rows failed, 'ERROR' if malformed")
    filename: str = Field(..., description="Original filename of uploaded CSV")
    file_size_bytes: int = Field(..., description="Size of uploaded file in bytes")
    total_rows: int = Field(..., description="Total data rows parsed excluding header")
    valid_rows: int = Field(..., description="Number of rows passing all schema checks")
    rejected_rows: int = Field(..., description="Number of rows rejected due to schema or constraint violations")
    errors: list[RowValidationError] = Field(default_factory=list, description="List of row-level errors")
    sample_valid_records: list[ValidatedPostingItem] = Field(default_factory=list, description="Sample of validated records (up to 5)")
    schema_version: str = Field("1.0", description="Target ingestion schema version")
    message: str = Field(..., description="Overall summary diagnostic message")

class ImportResponse(BaseModel):
    batch_id: str = Field(..., description="Unique generated ingestion batch identifier")
    filename: str = Field(..., description="Original uploaded CSV filename")
    status: str = Field(..., description="'COMPLETED', 'REJECTED', or 'DUPLICATE'")
    uploaded_at: str = Field(..., description="ISO 8601 UTC timestamp of import")
    total_rows: int = Field(..., description="Total rows in the CSV file")
    imported_rows: int = Field(..., description="Number of records persisted to database")
    rejected_rows: int = Field(..., description="Number of records rejected")
    file_hash: str = Field(..., description="SHA-256 content checksum of the imported batch")
    proposals_created: int = Field(0, description="Number of occupation review proposals generated")
    message: str = Field(..., description="Import result message")

class ImportBatchSummary(BaseModel):
    batch_id: str
    filename: str
    uploaded_at: str
    total_rows: int
    valid_rows: int
    rejected_rows: int
    status: str
    error_summary: str | None = None
