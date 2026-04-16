
-- Prerequisites : extension pgvector for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Creation of tables
CREATE TABLE tokens (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol          VARCHAR(20) NOT NULL UNIQUE,
    name            VARCHAR(100) NOT NULL,
    slug            VARCHAR(100) NOT NULL UNIQUE,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE price_snapshots (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_id        UUID NOT NULL REFERENCES tokens(id) ON DELETE CASCADE,
    price_usd       NUMERIC(20, 8) NOT NULL,
    market_cap      NUMERIC(30, 2),
    volume_24h      NUMERIC(30, 2),
    change_24h      NUMERIC(8, 4),
    scraped_at      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    source          VARCHAR(100) DEFAULT 'scraper'
);

CREATE TABLE news (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_id        UUID REFERENCES tokens(id) ON DELETE SET NULL,
    title           TEXT NOT NULL,
    content         TEXT,
    url             TEXT UNIQUE,
    source          VARCHAR(100),
    published_at    TIMESTAMP WITH TIME ZONE,
    scraped_at      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE embeddings_news (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    news_id         UUID NOT NULL REFERENCES news(id) ON DELETE CASCADE,
    embedding       vector(1536) NOT NULL,
    model           VARCHAR(100) NOT NULL DEFAULT 'text-embedding-3-small',
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Classical indexes

CREATE INDEX ON price_snapshots (token_id, scraped_at DESC);
CREATE INDEX ON news            (token_id, published_at DESC);
CREATE INDEX ON news            (scraped_at DESC);
CREATE INDEX ON news            (source);

-- Vectorial Indexes

CREATE INDEX ON embeddings_news USING hnsw (embedding vector_cosine_ops);