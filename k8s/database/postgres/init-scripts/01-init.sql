-- Forge Database Initialization
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;
-- pgvector extension not available in standard postgres image.
-- AI RAG features disabled for local dev, CRUD APIs fully functional.
