"""Seed academic structure data for Pakistan MBBS curriculum."""

from sqlalchemy.orm import Session

from app.models.academic import AcademicBlock, AcademicSubject, AcademicYear


def seed_academic_structure(db: Session) -> dict:
    """
    Seed the initial academic structure for Pakistan MBBS curriculum.

    This includes:
    - 5 Academic Years (1st Year, 2nd Year, 3rd Year, 4th Year, Final Year)
    - Blocks for each year (A, B, C for Year 1; D, E, F for Year 2; etc.)
    - Basic subjects for preclinical and clinical years

    Returns a summary of what was seeded.
    """
    stats = {"years": 0, "blocks": 0, "subjects": 0}

    # Check if data already exists
    existing_years = db.query(AcademicYear).count()
    if existing_years > 0:
        return {"message": "Academic structure already seeded", "skipped": True}

    # =========================================================================
    # Define Academic Years
    # =========================================================================
    years_data = [
        {"slug": "year1", "display_name": "1st Year", "sort_order": 1},
        {"slug": "year2", "display_name": "2nd Year", "sort_order": 2},
        {"slug": "year3", "display_name": "3rd Year", "sort_order": 3},
        {"slug": "year4", "display_name": "4th Year", "sort_order": 4},
        {"slug": "final", "display_name": "Final Year", "sort_order": 5},
    ]

    years = {}
    for year_data in years_data:
        year = AcademicYear(**year_data)
        db.add(year)
        db.flush()  # Get the ID
        years[year_data["slug"]] = year
        stats["years"] += 1

    # =========================================================================
    # Define Blocks per Year
    # =========================================================================
    blocks_data = {
        "year1": [
            {"code": "A", "display_name": "Block A", "sort_order": 1},
            {"code": "B", "display_name": "Block B", "sort_order": 2},
            {"code": "C", "display_name": "Block C", "sort_order": 3},
        ],
        "year2": [
            {"code": "D", "display_name": "Block D", "sort_order": 1},
            {"code": "E", "display_name": "Block E", "sort_order": 2},
            {"code": "F", "display_name": "Block F", "sort_order": 3},
        ],
        "year3": [
            {"code": "G", "display_name": "Block G", "sort_order": 1},
            {"code": "H", "display_name": "Block H", "sort_order": 2},
            {"code": "I", "display_name": "Block I", "sort_order": 3},
        ],
        "year4": [
            {"code": "J", "display_name": "Block J", "sort_order": 1},
            {"code": "K", "display_name": "Block K", "sort_order": 2},
            {"code": "L", "display_name": "Block L", "sort_order": 3},
        ],
        "final": [
            {"code": "M", "display_name": "Block M", "sort_order": 1},
            {"code": "N", "display_name": "Block N", "sort_order": 2},
            {"code": "O", "display_name": "Block O", "sort_order": 3},
        ],
    }

    for year_slug, blocks in blocks_data.items():
        year = years[year_slug]
        for block_data in blocks:
            block = AcademicBlock(year_id=year.id, **block_data)
            db.add(block)
            stats["blocks"] += 1

    # =========================================================================
    # Define Subjects per Year
    # =========================================================================
    subjects_data = {
        "year1": [
            {"code": "ANAT", "display_name": "Anatomy", "sort_order": 1},
            {"code": "PHYS", "display_name": "Physiology", "sort_order": 2},
            {"code": "BIOC", "display_name": "Biochemistry", "sort_order": 3},
        ],
        "year2": [
            {"code": "ANAT", "display_name": "Anatomy", "sort_order": 1},
            {"code": "PHYS", "display_name": "Physiology", "sort_order": 2},
            {"code": "BIOC", "display_name": "Biochemistry", "sort_order": 3},
        ],
        "year3": [
            {"code": "PATH", "display_name": "Pathology", "sort_order": 1},
            {"code": "PHRM", "display_name": "Pharmacology", "sort_order": 2},
            {"code": "FMED", "display_name": "Forensic Medicine", "sort_order": 3},
            {"code": "COMM", "display_name": "Community Medicine", "sort_order": 4},
        ],
        "year4": [
            {"code": "MED", "display_name": "Medicine", "sort_order": 1},
            {"code": "SURG", "display_name": "Surgery", "sort_order": 2},
            {"code": "OBGY", "display_name": "Obstetrics & Gynaecology", "sort_order": 3},
            {"code": "PAED", "display_name": "Paediatrics", "sort_order": 4},
            {"code": "OPTH", "display_name": "Ophthalmology", "sort_order": 5},
            {"code": "ENT", "display_name": "ENT", "sort_order": 6},
        ],
        "final": [
            {"code": "MED", "display_name": "Medicine", "sort_order": 1},
            {"code": "SURG", "display_name": "Surgery", "sort_order": 2},
            {"code": "OBGY", "display_name": "Obstetrics & Gynaecology", "sort_order": 3},
            {"code": "PAED", "display_name": "Paediatrics", "sort_order": 4},
        ],
    }

    for year_slug, subjects in subjects_data.items():
        year = years[year_slug]
        for subject_data in subjects:
            subject = AcademicSubject(year_id=year.id, **subject_data)
            db.add(subject)
            stats["subjects"] += 1

    db.commit()

    return {
        "message": "Academic structure seeded successfully",
        "skipped": False,
        "stats": stats,
    }


if __name__ == "__main__":
    # Allow running as standalone script
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        result = seed_academic_structure(db)
        print(result)
    finally:
        db.close()
