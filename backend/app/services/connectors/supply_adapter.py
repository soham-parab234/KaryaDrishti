"""Institutional Training Supply & Capacity CSV Adapter (Phase 11: Data Integration Readiness).

Validated adapter for ingesting vocational training seat allocations,
student enrollments, completions, and placements from State ITI Directorates,
Polytechnic Boards, and NCVET/SIP tracking reports.
"""

import csv
import io
import hashlib
from typing import Any
from sqlalchemy.orm import Session

from backend.app.services.connectors.base import BaseDataConnector, ConnectorMetadata
from backend.app.models.analytics import TrainingCapacityOutcome
from backend.app.models.occupation import NcoOccupation


class TrainingSupplyCsvAdapter(BaseDataConnector):
    """Adapter for institutional training capacity and graduate outcomes CSV format."""

    def get_metadata(self) -> ConnectorMetadata:
        return ConnectorMetadata(
            connector_id="TRAINING_SUPPLY_CSV_ADAPTER",
            connector_name="Institutional Training Capacity & Outcomes CSV Adapter",
            source_family="TRAINING_CAPACITY",
            connection_status="ACTIVE_LOCAL_ADAPTER",
            auth_mechanism="NONE_FILE_UPLOAD",
            is_live_connection=False,
            expected_schema={
                "nco_code": "string (NCO-2015 code, e.g. 7233.0100)",
                "district_code": "string (e.g. MH_PUN, MH_NSK)",
                "reporting_period": "string (YYYY-MM)",
                "sanctioned_seats": "integer (>= 0, sanctioned capacity)",
                "enrolled_students": "integer (>= 0, optional)",
                "completed_students": "integer (>= 0, optional)",
                "placed_students": "integer (>= 0, optional)",
                "source_system": "string (e.g. NCVET_SIP, DGT_MIS, STATE_ITI_PORTAL)",
            },
            description="Ingests institutional training capacity and graduation outcomes. In accordance with Master R&D Section 8, sanctioned seats represent capacity and are strictly distinguished from active market supply.",
            limitations_notice="Graduate counts do not automatically translate to available workers without factoring in labor force entry rates and local geographic retention.",
            verification_disclaimer="Imported records are flagged with data_status='IMPORTED' and explicitly distinguished from pilot baseline figures.",
        )

    def validate_input(self, content: bytes, filename: str = "training_supply.csv") -> dict[str, Any]:
        """Validate institutional training supply CSV structure and bounds."""
        errors: list[dict[str, Any]] = []
        valid_rows: list[dict[str, Any]] = []

        if not content:
            return {
                "is_valid": False,
                "status": "REJECTED",
                "filename": filename,
                "total_rows": 0,
                "valid_rows": 0,
                "rejected_rows": 0,
                "errors": [{"row_number": 0, "column_name": "file", "error_type": "EMPTY_FILE", "message": "File is completely empty"}],
                "message": "Uploaded training supply file is empty.",
            }

        file_hash = hashlib.sha256(content).hexdigest()
        
        # Decode
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                text = content.decode("latin-1")
            except Exception:
                return {
                    "is_valid": False,
                    "status": "ERROR",
                    "filename": filename,
                    "errors": [{"row_number": 0, "column_name": "encoding", "error_type": "DECODE_ERROR", "message": "Unsupported file encoding"}],
                }

        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            return {
                "is_valid": False,
                "status": "REJECTED",
                "filename": filename,
                "errors": [{"row_number": 1, "column_name": "headers", "error_type": "MISSING_HEADERS", "message": "CSV has no headers"}],
            }

        required_headers = {"nco_code", "district_code", "reporting_period", "sanctioned_seats", "source_system"}
        missing = required_headers - set(h.strip().lower() for h in reader.fieldnames if h)
        if missing:
            return {
                "is_valid": False,
                "status": "REJECTED",
                "filename": filename,
                "errors": [{"row_number": 1, "column_name": ", ".join(missing), "error_type": "MISSING_REQUIRED_COLUMNS", "message": f"Missing required headers: {missing}"}],
            }

        row_num = 1
        for raw_row in reader:
            row_num += 1
            row = {k.strip().lower(): (v.strip() if v else "") for k, v in raw_row.items() if k}

            nco_code = row.get("nco_code", "")
            district_code = row.get("district_code", "")
            reporting_period = row.get("reporting_period", "")
            sanctioned_seats_raw = row.get("sanctioned_seats", "")
            source_system = row.get("source_system", "STATE_MIS")

            if not nco_code:
                errors.append({"row_number": row_num, "column_name": "nco_code", "error_type": "REQUIRED", "message": "nco_code cannot be empty"})
            if not district_code:
                errors.append({"row_number": row_num, "column_name": "district_code", "error_type": "REQUIRED", "message": "district_code cannot be empty"})
            if not reporting_period or len(reporting_period) < 7:
                errors.append({"row_number": row_num, "column_name": "reporting_period", "error_type": "FORMAT", "message": "reporting_period must be YYYY-MM"})

            # Parse numeric fields
            try:
                seats = int(sanctioned_seats_raw)
                if seats < 0:
                    errors.append({"row_number": row_num, "column_name": "sanctioned_seats", "error_type": "RANGE", "message": "sanctioned_seats must be >= 0"})
            except ValueError:
                errors.append({"row_number": row_num, "column_name": "sanctioned_seats", "error_type": "TYPE", "message": "sanctioned_seats must be integer"})
                seats = 0

            enrolled = None
            if row.get("enrolled_students"):
                try:
                    enrolled = int(row["enrolled_students"])
                    if enrolled < 0:
                        errors.append({"row_number": row_num, "column_name": "enrolled_students", "error_type": "RANGE", "message": "enrolled_students must be >= 0"})
                except ValueError:
                    errors.append({"row_number": row_num, "column_name": "enrolled_students", "error_type": "TYPE", "message": "enrolled_students must be integer"})

            completed = None
            if row.get("completed_students"):
                try:
                    completed = int(row["completed_students"])
                    if completed < 0:
                        errors.append({"row_number": row_num, "column_name": "completed_students", "error_type": "RANGE", "message": "completed_students must be >= 0"})
                except ValueError:
                    errors.append({"row_number": row_num, "column_name": "completed_students", "error_type": "TYPE", "message": "completed_students must be integer"})

            placed = None
            if row.get("placed_students"):
                try:
                    placed = int(row["placed_students"])
                    if placed < 0:
                        errors.append({"row_number": row_num, "column_name": "placed_students", "error_type": "RANGE", "message": "placed_students must be >= 0"})
                except ValueError:
                    errors.append({"row_number": row_num, "column_name": "placed_students", "error_type": "TYPE", "message": "placed_students must be integer"})

            # Logical cross-field checks
            if enrolled is not None and completed is not None and completed > enrolled:
                errors.append({
                    "row_number": row_num,
                    "column_name": "completed_students",
                    "error_type": "LOGICAL_CONSTRAINT",
                    "message": f"completed_students ({completed}) cannot exceed enrolled_students ({enrolled})",
                })
            if completed is not None and placed is not None and placed > completed:
                errors.append({
                    "row_number": row_num,
                    "column_name": "placed_students",
                    "error_type": "LOGICAL_CONSTRAINT",
                    "message": f"placed_students ({placed}) cannot exceed completed_students ({completed})",
                })

            valid_rows.append({
                "nco_code": nco_code,
                "district_code": district_code,
                "reporting_period": reporting_period,
                "sanctioned_seats": seats,
                "enrolled_students": enrolled,
                "completed_students": completed,
                "placed_students": placed,
                "source_system": source_system,
            })

        is_valid = len(errors) == 0 and len(valid_rows) > 0
        return {
            "is_valid": is_valid,
            "status": "VALID" if is_valid else "REJECTED",
            "filename": filename,
            "file_size_bytes": len(content),
            "file_hash": file_hash,
            "total_rows": row_num - 1,
            "valid_rows": len(valid_rows) if is_valid else 0,
            "rejected_rows": len(errors),
            "errors": errors,
            "valid_records": valid_rows if is_valid else [],
            "message": f"Validation {'passed' if is_valid else 'failed'} with {len(errors)} error(s)."
        }

    def import_data(
        self,
        content: bytes,
        db: Session,
        filename: str = "training_supply.csv",
        **kwargs,
    ) -> dict[str, Any]:
        """Validate and persist clean training capacity outcome records."""
        val = self.validate_input(content, filename=filename)
        if not val["is_valid"]:
            raise ValueError(f"Training supply CSV validation failed: {val['message']}")

        records = val["valid_records"]
        persisted_count = 0

        for r in records:
            # Check or ensure occupation exists
            occ = db.query(NcoOccupation).filter(NcoOccupation.nco_code == r["nco_code"]).first()
            if not occ:
                # Create stub occupation record if missing so foreign key constraint holds
                occ = NcoOccupation(
                    nco_code=r["nco_code"],
                    canonical_title=f"Imported Trade {r['nco_code']}",
                    division_code=r["nco_code"][:1],
                    division_title="Imported Division",
                    source_status="IMPORTED",
                )
                db.add(occ)
                db.flush()

            # Upsert into TrainingCapacityOutcome
            existing = (
                db.query(TrainingCapacityOutcome)
                .filter(
                    TrainingCapacityOutcome.nco_code == r["nco_code"],
                    TrainingCapacityOutcome.district_code == r["district_code"],
                    TrainingCapacityOutcome.reporting_period == r["reporting_period"],
                    TrainingCapacityOutcome.source_system == r["source_system"],
                )
                .first()
            )

            placement_rate = None
            if r["completed_students"] and r["completed_students"] > 0 and r["placed_students"] is not None:
                placement_rate = round((r["placed_students"] / r["completed_students"]) * 100.0, 1)

            if existing:
                existing.sanctioned_seats = r["sanctioned_seats"]
                existing.enrolled_students = r["enrolled_students"]
                existing.completed_students = r["completed_students"]
                existing.placed_students = r["placed_students"]
                existing.placement_rate_pct = placement_rate
                existing.data_status = "IMPORTED"
            else:
                new_outcome = TrainingCapacityOutcome(
                    nco_code=r["nco_code"],
                    district_code=r["district_code"],
                    reporting_period=r["reporting_period"],
                    sanctioned_seats=r["sanctioned_seats"],
                    enrolled_students=r["enrolled_students"],
                    completed_students=r["completed_students"],
                    placed_students=r["placed_students"],
                    placement_rate_pct=placement_rate,
                    source_system=r["source_system"],
                    data_status="IMPORTED",
                    limitations="Imported institutional capacity record; verified via institutional batch adapter.",
                )
                db.add(new_outcome)
            persisted_count += 1

        db.commit()

        return {
            "status": "COMPLETED",
            "filename": filename,
            "records_persisted": persisted_count,
            "data_status": "IMPORTED",
            "message": f"Successfully ingested {persisted_count} institutional training capacity record(s).",
        }
