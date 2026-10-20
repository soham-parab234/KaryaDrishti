"""NCO-2015 Reference Taxonomy API Endpoints."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.app.db.session import get_db
from backend.app.models.occupation import NcoOccupation
from backend.app.schemas.occupation import (
    NcoOccupationItem,
    NcoReferenceListResponse,
    ReferenceImportSummary,
)
from backend.app.services.nco_reference import seed_pilot_baseline_nco, import_nco_csv

router = APIRouter(prefix="/occupations/reference", tags=["NCO Reference Taxonomy"])

@router.get(
    "",
    response_model=NcoReferenceListResponse,
    summary="List loaded NCO-2015 reference occupations",
)
def list_reference_occupations(
    q: str | None = Query(None, description="Search term across title, code, or aliases"),
    division: str | None = Query(None, description="Filter by NCO 1-digit division code (e.g. '7', '3')"),
    source_status: str | None = Query(None, description="Filter by provenance status (e.g. 'PILOT_BASELINE', 'OFFICIAL_DGE')"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> NcoReferenceListResponse:
    """List reference occupation records with optional search, division, and source filtering."""
    query = db.query(NcoOccupation)

    if division:
        query = query.filter(NcoOccupation.division_code == division)

    if source_status:
        query = query.filter(NcoOccupation.source_status == source_status)

    if q:
        search_pattern = f"%{q.strip().lower()}%"
        query = query.filter(
            or_(
                NcoOccupation.nco_code.ilike(search_pattern),
                NcoOccupation.canonical_title.ilike(search_pattern),
                NcoOccupation.division_title.ilike(search_pattern),
            )
        )

    total = query.count()
    occupations = query.order_by(NcoOccupation.nco_code).offset(offset).limit(limit).all()

    items = [
        NcoOccupationItem(
            nco_code=occ.nco_code,
            canonical_title=occ.canonical_title,
            division_code=occ.division_code,
            division_title=occ.division_title,
            sub_major_code=occ.sub_major_code,
            sub_major_title=occ.sub_major_title,
            minor_code=occ.minor_code,
            minor_title=occ.minor_title,
            unit_group_code=occ.unit_group_code,
            unit_group_title=occ.unit_group_title,
            description=occ.description,
            source_status=occ.source_status,
            is_verified=occ.is_verified,
            aliases=[a.alias_raw for a in occ.aliases],
        )
        for occ in occupations
    ]

    return NcoReferenceListResponse(total=total, items=items)

@router.get(
    "/{nco_code}",
    response_model=NcoOccupationItem,
    summary="Get detailed NCO reference record by code",
)
def get_reference_occupation(
    nco_code: str,
    db: Session = Depends(get_db),
) -> NcoOccupationItem:
    """Retrieve single NCO-2015 occupation record with complete hierarchy and registered aliases."""
    occ = db.query(NcoOccupation).filter(NcoOccupation.nco_code == nco_code).first()
    if not occ:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"NCO code '{nco_code}' not found in loaded reference taxonomy.",
        )

    return NcoOccupationItem(
        nco_code=occ.nco_code,
        canonical_title=occ.canonical_title,
        division_code=occ.division_code,
        division_title=occ.division_title,
        sub_major_code=occ.sub_major_code,
        sub_major_title=occ.sub_major_title,
        minor_code=occ.minor_code,
        minor_title=occ.minor_title,
        unit_group_code=occ.unit_group_code,
        unit_group_title=occ.unit_group_title,
        description=occ.description,
        source_status=occ.source_status,
        is_verified=occ.is_verified,
        aliases=[a.alias_raw for a in occ.aliases],
    )

@router.post(
    "/seed-baseline",
    summary="Seed verified Maharashtra pilot baseline NCO reference occupations",
)
def seed_baseline(db: Session = Depends(get_db)):
    """Seed or update the verified pilot baseline NCO occupations and aliases."""
    result = seed_pilot_baseline_nco(db)
    return {
        "status": "COMPLETED",
        "provenance": "PILOT_BASELINE",
        "occupations_added": result["occupations_added"],
        "aliases_added": result["aliases_added"],
        "message": "Verified Maharashtra pilot baseline NCO taxonomy seeded successfully.",
    }

@router.post(
    "/import",
    response_model=ReferenceImportSummary,
    summary="Import external NCO reference CSV file",
)
async def import_reference_taxonomy(
    file: UploadFile = File(..., description="NCO CSV file to import into reference store"),
    source_label: str = Query("OFFICIAL_DGE", description="Provenance label for the imported dataset"),
    db: Session = Depends(get_db),
) -> ReferenceImportSummary:
    """Import official NCO-2015 CSV taxonomy file into reference store with explicit provenance tracking."""
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No CSV file provided for reference import.",
        )

    content = await file.read()
    return import_nco_csv(content, file.filename, db, source_label=source_label)
