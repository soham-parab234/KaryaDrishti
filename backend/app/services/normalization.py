"""Deterministic Title Normalization & NCO-2015 Mapping Engine.

Conforms strictly to LMIS Master R&D Section 7:
1. Deterministic text cleaning (casing, punctuation, abbreviations, token normalization).
2. Exact matches against verified canonical titles and aliases take precedence.
3. Token overlap suggestions only when supported by reference records.
4. Preserves the original raw title for complete traceability.
5. Never silently approves uncertain matches.
"""

import re
from dataclasses import dataclass, field
from sqlalchemy.orm import Session
from backend.app.models.occupation import NcoOccupation, OccupationAlias
from backend.app.schemas.occupation import CandidateMatchItem

# Common domain abbreviation expansions
ABBREVIATION_MAP = {
    "sr": "senior",
    "jr": "junior",
    "tech": "technician",
    "mech": "mechanic",
    "exec": "executive",
    "asst": "assistant",
    "mgr": "manager",
    "engr": "engineer",
    "eng": "engineer",
    "dev": "developer",
    "op": "operator",
    "maint": "maintenance",
    "pv": "pv",
    "sol": "solar",
}

# Stopwords that should not artificially inflate token overlap
STOPWORDS = {
    "and",
    "or",
    "the",
    "in",
    "for",
    "at",
    "of",
    "to",
    "with",
    "level",
    "trainee",
    "lead",
    "associate",
    "specialist",
    "staff",
    "team",
}

@dataclass
class NormalizationResult:
    raw_title: str
    normalized_title: str
    status: str  # "UNMATCHED", "PROPOSED", "APPROVED"
    match_method: str  # "EXACT_CANONICAL", "EXACT_ALIAS", "TOKEN_OVERLAP", "NONE"
    confidence: float
    proposed_nco_code: str | None
    proposed_canonical_title: str | None
    match_rationale: str
    candidates: list[CandidateMatchItem] = field(default_factory=list)

def clean_title(raw_title: str) -> str:
    """Perform deterministic text cleaning on a raw job title."""
    if not raw_title:
        return ""

    # 1. Lowercase
    cleaned = raw_title.lower()

    # 2. Standardize symbols: replace ampersand with 'and'
    cleaned = re.sub(r"&", " and ", cleaned)

    # 3. Replace punctuation and non-alphanumerics with space
    cleaned = re.sub(r"[^\w\s]", " ", cleaned)

    # 4. Tokenize and expand abbreviations
    raw_tokens = cleaned.split()
    expanded_tokens = [ABBREVIATION_MAP.get(t, t) for t in raw_tokens]

    # 5. Join with single space
    return " ".join(expanded_tokens)

def extract_content_tokens(text: str) -> set[str]:
    """Extract informative non-stopword tokens from cleaned text."""
    tokens = text.lower().split()
    return {t for t in tokens if len(t) > 1 and t not in STOPWORDS}

def match_job_title(raw_title: str, db: Session) -> NormalizationResult:
    """Normalize and match a raw job title against the NCO-2015 reference store."""
    normalized = clean_title(raw_title)

    if not normalized:
        return NormalizationResult(
            raw_title=raw_title,
            normalized_title="",
            status="UNMATCHED",
            match_method="NONE",
            confidence=0.0,
            proposed_nco_code=None,
            proposed_canonical_title=None,
            match_rationale="Raw job title is empty or contains no alphanumeric tokens.",
        )

    # Step 1: Exact Canonical Match
    canonical_match = (
        db.query(NcoOccupation)
        .all()
    )
    for occ in canonical_match:
        if clean_title(occ.canonical_title) == normalized:
            candidate = CandidateMatchItem(
                nco_code=occ.nco_code,
                canonical_title=occ.canonical_title,
                matched_alias=None,
                match_method="EXACT_CANONICAL",
                confidence=100.0,
                rationale=f"Exact match with canonical NCO title '{occ.canonical_title}'.",
            )
            return NormalizationResult(
                raw_title=raw_title,
                normalized_title=normalized,
                status="PROPOSED",
                match_method="EXACT_CANONICAL",
                confidence=100.0,
                proposed_nco_code=occ.nco_code,
                proposed_canonical_title=occ.canonical_title,
                match_rationale=candidate.rationale,
                candidates=[candidate],
            )

    # Step 2: Exact Verified Alias Match
    exact_alias = (
        db.query(OccupationAlias)
        .filter(OccupationAlias.alias_normalized == normalized)
        .first()
    )
    if exact_alias:
        occ = exact_alias.occupation or db.query(NcoOccupation).filter(NcoOccupation.nco_code == exact_alias.nco_code).first()
        canonical_title = occ.canonical_title if occ else exact_alias.nco_code
        candidate = CandidateMatchItem(
            nco_code=exact_alias.nco_code,
            canonical_title=canonical_title,
            matched_alias=exact_alias.alias_raw,
            match_method="EXACT_ALIAS",
            confidence=98.0,
            rationale=f"Exact match with verified alias '{exact_alias.alias_raw}' for NCO {exact_alias.nco_code}.",
        )
        return NormalizationResult(
            raw_title=raw_title,
            normalized_title=normalized,
            status="PROPOSED",
            match_method="EXACT_ALIAS",
            confidence=98.0,
            proposed_nco_code=exact_alias.nco_code,
            proposed_canonical_title=canonical_title,
            match_rationale=candidate.rationale,
            candidates=[candidate],
        )

    # Step 3: Token Overlap Candidate Suggestion
    input_tokens = extract_content_tokens(normalized)
    if len(input_tokens) < 1:
        return NormalizationResult(
            raw_title=raw_title,
            normalized_title=normalized,
            status="UNMATCHED",
            match_method="NONE",
            confidence=0.0,
            proposed_nco_code=None,
            proposed_canonical_title=None,
            match_rationale="No distinct domain tokens found after stopword filtering.",
        )

    # Search known aliases and canonical titles in database
    all_aliases = db.query(OccupationAlias).all()
    all_occupations = db.query(NcoOccupation).all()

    scored_candidates: list[tuple[float, str, str, str | None, list[str]]] = []
    # (score, nco_code, canonical_title, matched_alias, matched_tokens)

    # Check aliases
    for alias in all_aliases:
        alias_tokens = extract_content_tokens(alias.alias_normalized)
        if not alias_tokens:
            continue
        intersection = input_tokens.intersection(alias_tokens)
        union = input_tokens.union(alias_tokens)
        if intersection and union:
            jaccard = len(intersection) / len(union)
            # Require at least 2 tokens matched OR > 60% overlap
            if (len(intersection) >= 2 and jaccard >= 0.4) or jaccard >= 0.6:
                occ = alias.occupation or db.query(NcoOccupation).filter(NcoOccupation.nco_code == alias.nco_code).first()
                title = occ.canonical_title if occ else alias.nco_code
                scored_candidates.append(
                    (jaccard, alias.nco_code, title, alias.alias_raw, sorted(list(intersection)))
                )

    # Check canonical titles
    for occ in all_occupations:
        occ_tokens = extract_content_tokens(clean_title(occ.canonical_title))
        if not occ_tokens:
            continue
        intersection = input_tokens.intersection(occ_tokens)
        union = input_tokens.union(occ_tokens)
        if intersection and union:
            jaccard = len(intersection) / len(union)
            if (len(intersection) >= 2 and jaccard >= 0.4) or jaccard >= 0.6:
                scored_candidates.append(
                    (jaccard, occ.nco_code, occ.canonical_title, None, sorted(list(intersection)))
                )

    if scored_candidates:
        # Sort by score descending
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        best = scored_candidates[0]
        best_score, best_code, best_title, best_alias, best_intersection = best

        # Deduplicate candidates by NCO code
        candidate_items: list[CandidateMatchItem] = []
        seen_codes: set[str] = set()
        for score, code, title, alias_raw, inter_tokens in scored_candidates:
            if code not in seen_codes:
                confidence_pct = round(score * 100, 1)
                match_desc = f"Token overlap [{', '.join(inter_tokens)}] with '{alias_raw or title}'."
                candidate_items.append(
                    CandidateMatchItem(
                        nco_code=code,
                        canonical_title=title,
                        matched_alias=alias_raw,
                        match_method="TOKEN_OVERLAP",
                        confidence=confidence_pct,
                        rationale=match_desc,
                    )
                )
                seen_codes.add(code)

        top_confidence = round(best_score * 100, 1)
        rationale = (
            f"Token overlap on key terms [{', '.join(best_intersection)}] with "
            f"reference record '{best_alias or best_title}' (NCO {best_code}). Awaiting human review."
        )

        return NormalizationResult(
            raw_title=raw_title,
            normalized_title=normalized,
            status="PROPOSED",
            match_method="TOKEN_OVERLAP",
            confidence=top_confidence,
            proposed_nco_code=best_code,
            proposed_canonical_title=best_title,
            match_rationale=rationale,
            candidates=candidate_items[:5],
        )

    # Step 4: Unmatched
    return NormalizationResult(
        raw_title=raw_title,
        normalized_title=normalized,
        status="UNMATCHED",
        match_method="NONE",
        confidence=0.0,
        proposed_nco_code=None,
        proposed_canonical_title=None,
        match_rationale="No exact match or supported candidate found in loaded NCO-2015 reference taxonomy.",
        candidates=[],
    )
