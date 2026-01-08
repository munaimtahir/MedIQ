-- Drop old blocks table and its dependencies
DROP TABLE IF EXISTS themes CASCADE;
DROP TABLE IF EXISTS blocks CASCADE;

-- Create new blocks table with correct schema
CREATE TABLE blocks (
    id SERIAL PRIMARY KEY,
    year_id INTEGER NOT NULL REFERENCES years(id) ON UPDATE CASCADE,
    code VARCHAR(50) NOT NULL,
    name VARCHAR(100) NOT NULL,
    order_no INTEGER NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT uq_block_year_code UNIQUE (year_id, code)
);

CREATE INDEX ix_blocks_year_order ON blocks(year_id, order_no);

-- Create new themes table
CREATE TABLE themes (
    id SERIAL PRIMARY KEY,
    block_id INTEGER NOT NULL REFERENCES blocks(id) ON UPDATE CASCADE,
    title VARCHAR(200) NOT NULL,
    order_no INTEGER NOT NULL,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT uq_theme_block_title UNIQUE (block_id, title)
);

CREATE INDEX ix_themes_block_order ON themes(block_id, order_no);
