"""Seed script for syllabus (Years and Blocks)."""

from sqlalchemy.orm import Session

from app.models.syllabus import Block, Year


def seed_syllabus_structure(db: Session) -> dict:
    """
    Seed default years and blocks.
    Creates: 1st Year, 2nd Year, 3rd Year, 4th Year, Final Year
    With blocks: A, B, C for 1st Year; D, E, F for 2nd Year
    """
    years_data = [
        {"name": "1st Year", "order_no": 1},
        {"name": "2nd Year", "order_no": 2},
        {"name": "3rd Year", "order_no": 3},
        {"name": "4th Year", "order_no": 4},
        {"name": "Final Year", "order_no": 5},
    ]

    blocks_data = [
        # 1st Year blocks
        {"year_name": "1st Year", "code": "A", "name": "Block A", "order_no": 1},
        {"year_name": "1st Year", "code": "B", "name": "Block B", "order_no": 2},
        {"year_name": "1st Year", "code": "C", "name": "Block C", "order_no": 3},
        # 2nd Year blocks
        {"year_name": "2nd Year", "code": "D", "name": "Block D", "order_no": 1},
        {"year_name": "2nd Year", "code": "E", "name": "Block E", "order_no": 2},
        {"year_name": "2nd Year", "code": "F", "name": "Block F", "order_no": 3},
    ]

    created_years = 0
    created_blocks = 0

    # Create years
    for year_data in years_data:
        existing = db.query(Year).filter(Year.name == year_data["name"]).first()
        if not existing:
            year = Year(
                name=year_data["name"],
                order_no=year_data["order_no"],
                is_active=True,
            )
            db.add(year)
            created_years += 1

    db.commit()

    # Create blocks (need to fetch year IDs after commit)
    year_map = {year.name: year.id for year in db.query(Year).all()}

    for block_data in blocks_data:
        year_id = year_map.get(block_data["year_name"])
        if not year_id:
            continue

        existing = (
            db.query(Block)
            .filter(Block.year_id == year_id, Block.code == block_data["code"])
            .first()
        )

        if not existing:
            block = Block(
                year_id=year_id,
                code=block_data["code"],
                name=block_data["name"],
                order_no=block_data["order_no"],
                is_active=True,
            )
            db.add(block)
            created_blocks += 1

    db.commit()

    return {
        "years_created": created_years,
        "blocks_created": created_blocks,
        "message": "Syllabus structure seeded successfully",
    }
