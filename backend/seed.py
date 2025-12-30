from database import SessionLocal
from models import Block, Question, Theme, User


def seed_database():
    db = SessionLocal()

    try:
        # Clear existing data (for development)
        db.query(Question).delete()
        db.query(Theme).delete()
        db.query(Block).delete()
        db.query(User).delete()
        db.commit()

        # Create users
        admin = User(id="admin-1", role="admin")
        student = User(id="student-1", role="student")
        db.add(admin)
        db.add(student)
        db.commit()

        # Create blocks for Year 1
        blocks_year1 = [
            ("A", "Anatomy", 1, "Human anatomy and structure"),
            ("B", "Biochemistry", 1, "Biochemical processes and molecules"),
            ("C", "Physiology", 1, "Body functions and systems"),
            ("D", "Pathology", 1, "Disease mechanisms"),
            ("E", "Pharmacology", 1, "Drugs and therapeutics"),
            ("F", "Microbiology", 1, "Microorganisms and infections"),
        ]

        # Create blocks for Year 2
        blocks_year2 = [
            ("A", "Advanced Anatomy", 2, "Advanced anatomical concepts"),
            ("B", "Clinical Biochemistry", 2, "Clinical applications"),
            ("C", "Clinical Physiology", 2, "Clinical physiology"),
            ("D", "Systemic Pathology", 2, "System-based pathology"),
            ("E", "Clinical Pharmacology", 2, "Clinical drug use"),
            ("F", "Clinical Microbiology", 2, "Clinical microbiology"),
        ]

        all_blocks = blocks_year1 + blocks_year2

        for block_id, name, year, desc in all_blocks:
            block = Block(id=block_id, name=name, year=year, description=desc)
            db.add(block)

        db.commit()

        # Create themes for each block
        theme_names = {
            "A": [
                "Cardiovascular System",
                "Respiratory System",
                "Digestive System",
                "Nervous System",
                "Musculoskeletal System",
                "Endocrine System",
                "Reproductive System",
                "Urinary System",
            ],
            "B": [
                "Proteins",
                "Enzymes",
                "Metabolism",
                "Nucleic Acids",
                "Lipids",
                "Carbohydrates",
                "Vitamins",
                "Minerals",
            ],
            "C": [
                "Cardiac Function",
                "Respiratory Function",
                "Renal Function",
                "Gastrointestinal Function",
                "Endocrine Function",
                "Nervous Function",
            ],
            "D": [
                "Inflammation",
                "Neoplasia",
                "Cardiovascular Pathology",
                "Respiratory Pathology",
                "Gastrointestinal Pathology",
                "Renal Pathology",
            ],
            "E": [
                "Cardiovascular Drugs",
                "Antimicrobials",
                "Analgesics",
                "Antihypertensives",
                "Antidiabetics",
                "Psychotropic Drugs",
            ],
            "F": [
                "Bacteria",
                "Viruses",
                "Fungi",
                "Parasites",
                "Antimicrobial Resistance",
                "Infection Control",
            ],
        }

        themes = []
        for block_id in ["A", "B", "C", "D", "E", "F"]:
            block = db.query(Block).filter(Block.id == block_id).first()
            if block:
                for theme_name in theme_names.get(block_id, [])[:6]:  # Limit to 6 themes per block
                    theme = Theme(
                        block_id=block_id, name=theme_name, description=f"Theme: {theme_name}"
                    )
                    db.add(theme)
                    themes.append(theme)

        db.commit()

        # Create sample questions
        sample_questions = [
            {
                "question_text": "Which of the following is the primary function of the heart?",
                "options": [
                    "Pumping blood throughout the body",
                    "Filtering waste products",
                    "Producing hormones",
                    "Digesting food",
                    "Storing energy",
                ],
                "correct_option_index": 0,
                "explanation": "The heart's primary function is to pump blood throughout the body via the circulatory system.",
                "tags": ["cardiovascular", "anatomy", "physiology"],
                "difficulty": "easy",
            },
            {
                "question_text": "What is the normal pH range of human blood?",
                "options": ["6.8 - 7.0", "7.0 - 7.2", "7.35 - 7.45", "7.5 - 7.8", "8.0 - 8.5"],
                "correct_option_index": 2,
                "explanation": "Human blood maintains a pH between 7.35 and 7.45, which is slightly alkaline.",
                "tags": ["biochemistry", "physiology", "acid-base"],
                "difficulty": "medium",
            },
            {
                "question_text": "Which enzyme is responsible for converting angiotensin I to angiotensin II?",
                "options": [
                    "Renin",
                    "ACE (Angiotensin Converting Enzyme)",
                    "Aldosterone",
                    "ADH",
                    "ANP",
                ],
                "correct_option_index": 1,
                "explanation": "ACE (Angiotensin Converting Enzyme) converts angiotensin I to the active angiotensin II.",
                "tags": ["pharmacology", "cardiovascular", "renin-angiotensin"],
                "difficulty": "hard",
            },
            {
                "question_text": "What is the most common cause of community-acquired pneumonia?",
                "options": [
                    "Streptococcus pneumoniae",
                    "Escherichia coli",
                    "Staphylococcus aureus",
                    "Pseudomonas aeruginosa",
                    "Klebsiella pneumoniae",
                ],
                "correct_option_index": 0,
                "explanation": "Streptococcus pneumoniae is the most common bacterial cause of community-acquired pneumonia.",
                "tags": ["microbiology", "respiratory", "infectious-disease"],
                "difficulty": "medium",
            },
            {
                "question_text": "Which of the following is a characteristic feature of malignant tumors?",
                "options": [
                    "Well-defined borders",
                    "Slow growth rate",
                    "Metastasis",
                    "Encapsulation",
                    "Differentiated cells",
                ],
                "correct_option_index": 2,
                "explanation": "Metastasis, the spread of cancer cells to distant sites, is a key characteristic of malignant tumors.",
                "tags": ["pathology", "oncology", "neoplasia"],
                "difficulty": "medium",
            },
        ]

        # Add more questions to reach ~30
        additional_questions = [
            {
                "question_text": "The primary site of gas exchange in the lungs is:",
                "options": ["Trachea", "Bronchi", "Alveoli", "Bronchioles", "Pleura"],
                "correct_option_index": 2,
                "explanation": "Alveoli are the tiny air sacs where gas exchange occurs between air and blood.",
                "tags": ["respiratory", "anatomy", "physiology"],
                "difficulty": "easy",
            },
            {
                "question_text": "Which vitamin deficiency causes scurvy?",
                "options": ["Vitamin A", "Vitamin B12", "Vitamin C", "Vitamin D", "Vitamin K"],
                "correct_option_index": 2,
                "explanation": "Scurvy is caused by a deficiency of vitamin C (ascorbic acid).",
                "tags": ["biochemistry", "nutrition", "vitamins"],
                "difficulty": "easy",
            },
            {
                "question_text": "The glomerular filtration rate (GFR) is primarily regulated by:",
                "options": [
                    "ADH",
                    "Aldosterone",
                    "Renin-angiotensin system",
                    "ANP",
                    "Parathyroid hormone",
                ],
                "correct_option_index": 2,
                "explanation": "The renin-angiotensin system plays a key role in regulating GFR and renal blood flow.",
                "tags": ["renal", "physiology", "pharmacology"],
                "difficulty": "hard",
            },
        ]

        all_questions = sample_questions + additional_questions

        # Get themes to assign questions to
        year1_themes = db.query(Theme).join(Block).filter(Block.year == 1).all()

        question_count = 0
        for i, q_data in enumerate(all_questions * 4):  # Repeat to get ~30 questions
            if question_count >= 30:
                break

            theme = year1_themes[i % len(year1_themes)]
            question = Question(
                theme_id=theme.id,
                question_text=q_data["question_text"],
                options=q_data["options"],
                correct_option_index=q_data["correct_option_index"],
                explanation=q_data["explanation"],
                tags=q_data["tags"],
                difficulty=q_data["difficulty"],
                is_published=True,  # Publish all seeded questions
            )
            db.add(question)
            question_count += 1

        db.commit()
        print(
            f"Seeded database with {len(all_blocks)} blocks, {len(themes)} themes, and {question_count} questions"
        )

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
