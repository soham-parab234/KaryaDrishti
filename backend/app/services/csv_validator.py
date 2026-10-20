"""CSV ingestion and validation service.

Conforms strictly to the canonical schema defined in LMIS Master R&D and
frontend INGESTION_SCHEMA_FIELDS:
- posting_id: Unique non-empty identifier (1-100 chars)
- raw_title: Length 3-150 chars
- district_code: Standard census/state district code (e.g. MH_PUN, MH_NSK)
- observation_date: Valid calendar date <= current date (YYYY-MM-DD)
- source_system: One of NCS_FEED, PORTAL_SCRAPE, SCHEME_MIS, ENTERPRISE_SURVEY
- vacancy_count: Integer >= 1 (defaults to 1 if blank or omitted)
"""

import csv
import io
import hashlib
from datetime import datetime, date, timezone
from dataclasses import dataclass, field

from backend.app.core.config import settings
from backend.app.schemas.ingestion import RowValidationError, ValidatedPostingItem

@dataclass
class CsvValidationResult:
    is_valid: bool
    status: str
    filename: str
    file_size_bytes: int
    file_hash: str
    total_rows: int
    valid_rows: int
    rejected_rows: int
    errors: list[RowValidationError] = field(default_factory=list)
    valid_records: list[ValidatedPostingItem] = field(default_factory=list)
    message: str = ""

def decode_file_bytes(content: bytes) -> tuple[str | None, str | None]:
    """Decode raw bytes into a string, trying utf-8-sig (with BOM), utf-8, then latin-1."""
    if not content:
        return "", None

    for enc in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
        try:
            decoded = content.decode(enc)
            # Ensure any lingering BOM zero-width space is stripped from beginning of file
            return decoded.lstrip("\ufeff"), enc
        except UnicodeDecodeError:
            continue
    return None, None

def validate_csv_content(
    content: bytes,
    filename: str = "upload.csv",
    reference_today: date | None = None,
) -> CsvValidationResult:
    """Validate a CSV file in-memory against schema rules, edge cases, and constraints."""
    today = reference_today or datetime.now(timezone.utc).date()
    file_size = len(content)
    file_hash = hashlib.sha256(content).hexdigest()

    # 1. File size enforcement
    if file_size > settings.MAX_UPLOAD_SIZE_BYTES:
        return CsvValidationResult(
            is_valid=False,
            status="ERROR",
            filename=filename,
            file_size_bytes=file_size,
            file_hash=file_hash,
            total_rows=0,
            valid_rows=0,
            rejected_rows=0,
            errors=[
                RowValidationError(
                    row_number=0,
                    field="file_size",
                    error_message=f"File size ({file_size / (1024 * 1024):.2f} MB) exceeds maximum allowed limit of {settings.MAX_UPLOAD_SIZE_BYTES / (1024 * 1024):.0f} MB.",
                    raw_value=str(file_size),
                )
            ],
            message="File size exceeds limit.",
        )

    # 2. Empty file check
    if file_size == 0:
        return CsvValidationResult(
            is_valid=False,
            status="ERROR",
            filename=filename,
            file_size_bytes=0,
            file_hash=file_hash,
            total_rows=0,
            valid_rows=0,
            rejected_rows=0,
            errors=[
                RowValidationError(
                    row_number=0,
                    field="file",
                    error_message="The provided CSV file is completely empty (0 bytes).",
                    raw_value="",
                )
            ],
            message="Uploaded file is empty.",
        )

    # 3. Decode encoding
    text_content, encoding_used = decode_file_bytes(content)
    if text_content is None:
        return CsvValidationResult(
            is_valid=False,
            status="ERROR",
            filename=filename,
            file_size_bytes=file_size,
            file_hash=file_hash,
            total_rows=0,
            valid_rows=0,
            rejected_rows=0,
            errors=[
                RowValidationError(
                    row_number=0,
                    field="encoding",
                    error_message="Unsupported file encoding. Please save CSV as UTF-8.",
                    raw_value="",
                )
            ],
            message="Unsupported text encoding.",
        )

    # 4. CSV parsing and delimiter sniffing
    try:
        sample = text_content[:4096]
        # Detect delimiter if possible, default to comma
        try:
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(sample, delimiters=",\t;")
        except Exception:
            dialect = csv.excel

        reader = csv.reader(io.StringIO(text_content), dialect)
        raw_rows = list(reader)
    except Exception as exc:
        return CsvValidationResult(
            is_valid=False,
            status="ERROR",
            filename=filename,
            file_size_bytes=file_size,
            file_hash=file_hash,
            total_rows=0,
            valid_rows=0,
            rejected_rows=0,
            errors=[
                RowValidationError(
                    row_number=0,
                    field="csv_structure",
                    error_message=f"Malformed CSV syntax or unclosed quotes: {str(exc)}",
                    raw_value="",
                )
            ],
            message="Malformed CSV file.",
        )

    # Check if file has any rows
    if not raw_rows:
        return CsvValidationResult(
            is_valid=False,
            status="ERROR",
            filename=filename,
            file_size_bytes=file_size,
            file_hash=file_hash,
            total_rows=0,
            valid_rows=0,
            rejected_rows=0,
            errors=[
                RowValidationError(
                    row_number=0,
                    field="file",
                    error_message="CSV file contains no rows.",
                    raw_value="",
                )
            ],
            message="No rows detected in file.",
        )

    # 5. Header row validation
    raw_header = raw_rows[0]
    cleaned_header = [h.strip().lstrip("\ufeff").lower() for h in raw_header]

    # Check duplicate headers
    seen_headers: set[str] = set()
    duplicate_headers: list[str] = []
    for h in cleaned_header:
        if h in seen_headers:
            duplicate_headers.append(h)
        seen_headers.add(h)

    if duplicate_headers:
        return CsvValidationResult(
            is_valid=False,
            status="ERROR",
            filename=filename,
            file_size_bytes=file_size,
            file_hash=file_hash,
            total_rows=0,
            valid_rows=0,
            rejected_rows=0,
            errors=[
                RowValidationError(
                    row_number=1,
                    field="header",
                    error_message=f"Duplicate column header(s) detected: {sorted(list(set(duplicate_headers)))}.",
                    raw_value=", ".join(raw_header),
                )
            ],
            message="Duplicate column headers detected.",
        )

    # Check required columns
    missing_columns = [col for col in settings.REQUIRED_CSV_COLUMNS if col not in cleaned_header]
    if missing_columns:
        return CsvValidationResult(
            is_valid=False,
            status="ERROR",
            filename=filename,
            file_size_bytes=file_size,
            file_hash=file_hash,
            total_rows=0,
            valid_rows=0,
            rejected_rows=0,
            errors=[
                RowValidationError(
                    row_number=1,
                    field="header",
                    error_message=f"Missing required column(s): {missing_columns}. Required schema: {list(settings.REQUIRED_CSV_COLUMNS)}.",
                    raw_value=", ".join(raw_header),
                )
            ],
            message=f"Missing required columns: {', '.join(missing_columns)}.",
        )

    header_index_map = {col: idx for idx, col in enumerate(cleaned_header)}

    # 6. Row-level iteration and validation
    row_errors: list[RowValidationError] = []
    valid_records: list[ValidatedPostingItem] = []
    seen_posting_ids: dict[str, int] = {}

    data_rows = raw_rows[1:]
    total_data_rows = len(data_rows)

    if total_data_rows == 0:
        return CsvValidationResult(
            is_valid=False,
            status="INVALID",
            filename=filename,
            file_size_bytes=file_size,
            file_hash=file_hash,
            total_rows=0,
            valid_rows=0,
            rejected_rows=0,
            errors=[
                RowValidationError(
                    row_number=1,
                    field="content",
                    error_message="CSV contains header row but zero data records.",
                    raw_value="",
                )
            ],
            message="No data rows found in CSV.",
        )

    rejected_row_numbers: set[int] = set()

    for row_idx, row in enumerate(data_rows, start=2):  # line 2 is first data row
        # Skip completely empty trailing lines
        if not row or all(c.strip() == "" for c in row):
            total_data_rows -= 1
            continue

        # Column count check
        if len(row) != len(raw_header):
            row_errors.append(
                RowValidationError(
                    row_number=row_idx,
                    field="row_structure",
                    error_message=f"Malformed row: expected {len(raw_header)} columns, found {len(row)}.",
                    raw_value=",".join(row),
                )
            )
            rejected_row_numbers.add(row_idx)
            continue

        row_has_error = False

        # Extract values
        posting_id_val = row[header_index_map["posting_id"]].strip()
        raw_title_val = row[header_index_map["raw_title"]].strip()
        district_code_val = row[header_index_map["district_code"]].strip().upper()
        date_val = row[header_index_map["observation_date"]].strip()
        source_val = row[header_index_map["source_system"]].strip().upper()

        vacancy_val_raw = (
            row[header_index_map["vacancy_count"]].strip()
            if "vacancy_count" in header_index_map
            else ""
        )

        # 6a. posting_id checks
        if not posting_id_val:
            row_errors.append(
                RowValidationError(
                    row_number=row_idx,
                    field="posting_id",
                    error_message="Mandatory field `posting_id` is empty or whitespace.",
                    raw_value=posting_id_val,
                )
            )
            row_has_error = True
        elif len(posting_id_val) > 100:
            row_errors.append(
                RowValidationError(
                    row_number=row_idx,
                    field="posting_id",
                    error_message=f"Value for `posting_id` exceeds 100 characters ({len(posting_id_val)} chars).",
                    raw_value=posting_id_val,
                )
            )
            row_has_error = True
        elif posting_id_val in seen_posting_ids:
            first_seen = seen_posting_ids[posting_id_val]
            row_errors.append(
                RowValidationError(
                    row_number=row_idx,
                    field="posting_id",
                    error_message=f"Duplicate `posting_id` '{posting_id_val}' detected within batch (previously observed on row {first_seen}).",
                    raw_value=posting_id_val,
                )
            )
            row_has_error = True
        else:
            seen_posting_ids[posting_id_val] = row_idx

        # 6b. raw_title checks
        if not raw_title_val:
            row_errors.append(
                RowValidationError(
                    row_number=row_idx,
                    field="raw_title",
                    error_message="Mandatory field `raw_title` is empty or null.",
                    raw_value=raw_title_val,
                )
            )
            row_has_error = True
        elif len(raw_title_val) < 3:
            row_errors.append(
                RowValidationError(
                    row_number=row_idx,
                    field="raw_title",
                    error_message=f"Value for `raw_title` is too short ({len(raw_title_val)} chars; minimum 3 chars required).",
                    raw_value=raw_title_val,
                )
            )
            row_has_error = True
        elif len(raw_title_val) > 150:
            row_errors.append(
                RowValidationError(
                    row_number=row_idx,
                    field="raw_title",
                    error_message=f"Value for `raw_title` exceeds maximum permitted length of 150 characters ({len(raw_title_val)} chars).",
                    raw_value=raw_title_val[:30] + "...",
                )
            )
            row_has_error = True

        # 6c. district_code checks
        if not district_code_val:
            row_errors.append(
                RowValidationError(
                    row_number=row_idx,
                    field="district_code",
                    error_message="Mandatory field `district_code` is empty.",
                    raw_value=district_code_val,
                )
            )
            row_has_error = True
        elif not settings.DISTRICT_CODE_PATTERN.match(district_code_val):
            row_errors.append(
                RowValidationError(
                    row_number=row_idx,
                    field="district_code",
                    error_message=f"Invalid district code `{district_code_val}`: does not conform to census standard (e.g. MH_PUN, MH_NSK).",
                    raw_value=district_code_val,
                )
            )
            row_has_error = True

        # 6d. observation_date checks
        if not date_val:
            row_errors.append(
                RowValidationError(
                    row_number=row_idx,
                    field="observation_date",
                    error_message="Mandatory field `observation_date` is empty.",
                    raw_value=date_val,
                )
            )
            row_has_error = True
        else:
            try:
                parsed_date = datetime.strptime(date_val, "%Y-%m-%d").date()
                if parsed_date > today:
                    row_errors.append(
                        RowValidationError(
                            row_number=row_idx,
                            field="observation_date",
                            error_message=f"Observation date `{date_val}` is in the future (current system date: {today}).",
                            raw_value=date_val,
                        )
                    )
                    row_has_error = True
            except ValueError:
                row_errors.append(
                    RowValidationError(
                        row_number=row_idx,
                        field="observation_date",
                        error_message=f"Invalid date format `{date_val}`: must be valid calendar date in YYYY-MM-DD format.",
                        raw_value=date_val,
                    )
                )
                row_has_error = True

        # 6e. source_system checks
        if not source_val:
            row_errors.append(
                RowValidationError(
                    row_number=row_idx,
                    field="source_system",
                    error_message="Mandatory field `source_system` is empty.",
                    raw_value=source_val,
                )
            )
            row_has_error = True
        elif source_val not in settings.ALLOWED_SOURCE_SYSTEMS:
            row_errors.append(
                RowValidationError(
                    row_number=row_idx,
                    field="source_system",
                    error_message=f"Invalid source_system `{source_val}`: must be one of {list(settings.ALLOWED_SOURCE_SYSTEMS)}.",
                    raw_value=source_val,
                )
            )
            row_has_error = True

        # 6f. vacancy_count checks (defaults to 1 if blank)
        vacancy_count = 1
        if vacancy_val_raw:
            try:
                vacancy_count = int(vacancy_val_raw)
                if vacancy_count < 1:
                    row_errors.append(
                        RowValidationError(
                            row_number=row_idx,
                            field="vacancy_count",
                            error_message=f"Invalid vacancy_count `{vacancy_val_raw}`: must be integer >= 1.",
                            raw_value=vacancy_val_raw,
                        )
                    )
                    row_has_error = True
            except ValueError:
                row_errors.append(
                    RowValidationError(
                        row_number=row_idx,
                        field="vacancy_count",
                        error_message=f"Invalid vacancy_count `{vacancy_val_raw}`: must be a valid integer.",
                        raw_value=vacancy_val_raw,
                    )
                )
                row_has_error = True

        if row_has_error:
            rejected_row_numbers.add(row_idx)
        else:
            valid_records.append(
                ValidatedPostingItem(
                    posting_id=posting_id_val,
                    raw_title=raw_title_val,
                    district_code=district_code_val,
                    observation_date=date_val,
                    source_system=source_val,
                    vacancy_count=vacancy_count,
                )
            )

    rejected_count = len(rejected_row_numbers)
    valid_count = len(valid_records)
    is_valid = (rejected_count == 0) and (valid_count > 0)
    status = "VALID" if is_valid else "INVALID"

    summary_message = (
        f"Validation passed: All {valid_count} rows conform to schema 1.0."
        if is_valid
        else f"Validation failed: {rejected_count} of {total_data_rows} rows rejected due to schema or constraint violations."
    )

    return CsvValidationResult(
        is_valid=is_valid,
        status=status,
        filename=filename,
        file_size_bytes=file_size,
        file_hash=file_hash,
        total_rows=total_data_rows,
        valid_rows=valid_count,
        rejected_rows=rejected_count,
        errors=row_errors,
        valid_records=valid_records,
        message=summary_message,
    )
