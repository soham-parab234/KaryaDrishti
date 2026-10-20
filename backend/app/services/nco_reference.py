"""NCO-2015 Reference Taxonomy Service.

Handles loading, seeding, and querying authoritative occupation definitions,
classification hierarchies, and verified aliases.
Conforms strictly to Directorate General of Employment (DGE) standards.
"""

import csv
import io
import re
from sqlalchemy.orm import Session
from backend.app.models.occupation import NcoOccupation, OccupationAlias
from backend.app.schemas.occupation import ReferenceImportSummary

# Deterministic cleaning for alias normalization
def normalize_string_key(text: str) -> str:
    """Normalize a title or alias for exact index matching."""
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    return " ".join(cleaned.split())

# Verified pilot baseline definitions from LMIS Master R&D and AI Handoff Summary
PILOT_BASELINE_OCCUPATIONS = [
    {
        "nco_code": "7421.0301",
        "canonical_title": "Solar PV Installation & Maintenance Technician",
        "division_code": "7",
        "division_title": "Craft and Related Trades Workers",
        "sub_major_code": "74",
        "sub_major_title": "Electrical and Electronic Trades Workers",
        "minor_code": "742",
        "minor_title": "Electronics and Telecommunications Installers and Repairers",
        "unit_group_code": "7421",
        "unit_group_title": "Electronics Mechanics, Fitters and Servicers",
        "description": "Installs, configures, tests, and maintains distributed rooftop and ground-mounted solar photovoltaic electrical systems, inverters, and battery banks.",
        "source_status": "PILOT_BASELINE",
        "is_verified": True,
        "aliases": [
            "Solar Rooftop Technician",
            "Solar PV Installer",
            "Solar Panel Maintenance Executive",
            "Solar Electrician Level 4",
            "Agri-Solar Pump Technician",
            "Solar PV System Installer",
        ],
    },
    {
        "nco_code": "7233.0100",
        "canonical_title": "Industrial Machinery Maintenance Mechanic",
        "division_code": "7",
        "division_title": "Craft and Related Trades Workers",
        "sub_major_code": "72",
        "sub_major_title": "Metal, Machinery and Related Trades Workers",
        "minor_code": "723",
        "minor_title": "Machinery Mechanics and Repairers",
        "unit_group_code": "7233",
        "unit_group_title": "Agricultural and Industrial Machinery Mechanics and Fitters",
        "description": "Performs scheduled servicing, calibration, overhaul, and repair on industrial manufacturing machinery, hydraulic presses, and automated CNC tooling systems.",
        "source_status": "PILOT_BASELINE",
        "is_verified": True,
        "aliases": [
            "Industrial Maintenance Mechanic",
            "CNC Machine Maintenance Fitter",
            "Plant Equipment Maintenance Technician",
            "Mechanical Maintenance Fitter",
            "CNC Mechanical Plant Service Fitter",
        ],
    },
    {
        "nco_code": "3511.0101",
        "canonical_title": "Computer Operations & Data Processing Specialist",
        "division_code": "3",
        "division_title": "Technicians and Associate Professionals",
        "sub_major_code": "35",
        "sub_major_title": "Information and Communications Technology Technicians",
        "minor_code": "351",
        "minor_title": "Information and Communications Technology Operations and User Support Technicians",
        "unit_group_code": "3511",
        "unit_group_title": "Information and Communications Technology Operations Technicians",
        "description": "Controls and monitors computer systems, peripheral equipment, database batch processing, and data verification routines.",
        "source_status": "PILOT_BASELINE",
        "is_verified": True,
        "aliases": [
            "Data Operations Associate",
            "Data Entry Specialist",
            "Junior MIS Operations Assistant",
            "Computer Systems Operator",
            "Junior Data Clerk / Back Office MIS",
        ],
    },
]

def seed_pilot_baseline_nco(db: Session) -> dict[str, int]:
    """Seed the database with verified pilot baseline NCO records if absent."""
    occupations_added = 0
    aliases_added = 0

    for item in PILOT_BASELINE_OCCUPATIONS:
        existing = db.query(NcoOccupation).filter(NcoOccupation.nco_code == item["nco_code"]).first()
        if not existing:
            occ = NcoOccupation(
                nco_code=item["nco_code"],
                canonical_title=item["canonical_title"],
                division_code=item["division_code"],
                division_title=item["division_title"],
                sub_major_code=item["sub_major_code"],
                sub_major_title=item["sub_major_title"],
                minor_code=item["minor_code"],
                minor_title=item["minor_title"],
                unit_group_code=item["unit_group_code"],
                unit_group_title=item["unit_group_title"],
                description=item["description"],
                source_status=item["source_status"],
                is_verified=item["is_verified"],
            )
            db.add(occ)
            db.flush()
            occupations_added += 1

            for alias_str in item["aliases"]:
                alias = OccupationAlias(
                    nco_code=item["nco_code"],
                    alias_raw=alias_str,
                    alias_normalized=normalize_string_key(alias_str),
                    source="PILOT_CURATED",
                    is_verified=True,
                )
                db.add(alias)
                aliases_added += 1
        else:
            # Check for any missing aliases on existing occupation
            for alias_str in item["aliases"]:
                norm = normalize_string_key(alias_str)
                exists_alias = (
                    db.query(OccupationAlias)
                    .filter(
                        OccupationAlias.nco_code == item["nco_code"],
                        OccupationAlias.alias_normalized == norm,
                    )
                    .first()
                )
                if not exists_alias:
                    alias = OccupationAlias(
                        nco_code=item["nco_code"],
                        alias_raw=alias_str,
                        alias_normalized=norm,
                        source="PILOT_CURATED",
                        is_verified=True,
                    )
                    db.add(alias)
                    aliases_added += 1

    db.commit()
    return {"occupations_added": occupations_added, "aliases_added": aliases_added}

def import_nco_csv(
    content: bytes,
    filename: str,
    db: Session,
    source_label: str = "OFFICIAL_DGE",
) -> ReferenceImportSummary:
    """Import official NCO-2015 CSV taxonomy file into reference store.

    Expected CSV columns:
    - nco_code
    - canonical_title
    - division_code
    - division_title
    Optional:
    - sub_major_code, sub_major_title, minor_code, minor_title, unit_group_code, unit_group_title
    - description
    - aliases (pipe-separated: 'alias 1|alias 2')
    """
    text_content = content.decode("utf-8-sig", errors="replace")
    reader = csv.reader(io.StringIO(text_content))
    rows = list(reader)

    if not rows or len(rows) < 2:
        return ReferenceImportSummary(
            filename=filename,
            source_status=source_label,
            occupations_imported=0,
            aliases_imported=0,
            message="CSV is empty or missing data rows.",
        )

    header = [h.strip().lower() for h in rows[0]]
    header_map = {col: idx for idx, col in enumerate(header)}

    required_cols = ["nco_code", "canonical_title", "division_code", "division_title"]
    missing = [c for c in required_cols if c not in header_map]
    if missing:
        return ReferenceImportSummary(
            filename=filename,
            source_status=source_label,
            occupations_imported=0,
            aliases_imported=0,
            message=f"Missing required columns in NCO CSV: {missing}",
        )

    occupations_imported = 0
    aliases_imported = 0

    for row in rows[1:]:
        if not row or all(c.strip() == "" for c in row):
            continue

        nco_code = row[header_map["nco_code"]].strip()
        canonical_title = row[header_map["canonical_title"]].strip()
        division_code = row[header_map["division_code"]].strip()
        division_title = row[header_map["division_title"]].strip()

        if not nco_code or not canonical_title:
            continue

        # Optional hierarchy fields
        sub_major_code = row[header_map["sub_major_code"]].strip() if "sub_major_code" in header_map else None
        sub_major_title = row[header_map["sub_major_title"]].strip() if "sub_major_title" in header_map else None
        minor_code = row[header_map["minor_code"]].strip() if "minor_code" in header_map else None
        minor_title = row[header_map["minor_title"]].strip() if "minor_title" in header_map else None
        unit_group_code = row[header_map["unit_group_code"]].strip() if "unit_group_code" in header_map else None
        unit_group_title = row[header_map["unit_group_title"]].strip() if "unit_group_title" in header_map else None
        description = row[header_map["description"]].strip() if "description" in header_map else None

        existing_occ = db.query(NcoOccupation).filter(NcoOccupation.nco_code == nco_code).first()
        if not existing_occ:
            occ = NcoOccupation(
                nco_code=nco_code,
                canonical_title=canonical_title,
                division_code=division_code,
                division_title=division_title,
                sub_major_code=sub_major_code,
                sub_major_title=sub_major_title,
                minor_code=minor_code,
                minor_title=minor_title,
                unit_group_code=unit_group_code,
                unit_group_title=unit_group_title,
                description=description,
                source_status=source_label,
                is_verified=True,
            )
            db.add(occ)
            occupations_imported += 1

        # Process pipe or comma separated aliases
        if "aliases" in header_map and row[header_map["aliases"]].strip():
            raw_aliases_field = row[header_map["aliases"]].strip()
            # Split by | or ;
            alias_tokens = re.split(r"[|;]", raw_aliases_field)
            for a_token in alias_tokens:
                alias_clean = a_token.strip()
                if alias_clean:
                    norm = normalize_string_key(alias_clean)
                    existing_alias = (
                        db.query(OccupationAlias)
                        .filter(
                            OccupationAlias.nco_code == nco_code,
                            OccupationAlias.alias_normalized == norm,
                        )
                        .first()
                    )
                    if not existing_alias:
                        db.add(
                            OccupationAlias(
                                nco_code=nco_code,
                                alias_raw=alias_clean,
                                alias_normalized=norm,
                                source="DGE_OFFICIAL",
                                is_verified=True,
                            )
                        )
                        aliases_imported += 1

    db.commit()

    return ReferenceImportSummary(
        filename=filename,
        source_status=source_label,
        occupations_imported=occupations_imported,
        aliases_imported=aliases_imported,
        message=f"Successfully imported {occupations_imported} NCO occupations and {aliases_imported} aliases.",
    )
