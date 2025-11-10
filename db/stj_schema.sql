CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE stj_decisoes (
    id SERIAL PRIMARY KEY,
    numero_processo VARCHAR(50),
    classe VARCHAR(100),
    orgao_julgador VARCHAR(150),
    relator VARCHAR(150),
    data_julgamento DATE,
    ementa TEXT,
    integra_decisao TEXT,
    embedding VECTOR(1536)
);
