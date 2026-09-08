-- Postgres schema for BitNote, equivalent to the SQLite schema in the
-- README's "Getting Started" section. Run once against a fresh database
-- when DB_PROVIDER=postgres, e.g.:
--   psql "$DATABASE_URL" -f schema_postgres.sql

CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    username TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT,
    created_at INTEGER DEFAULT EXTRACT(EPOCH FROM NOW())::INTEGER
);

CREATE TABLE IF NOT EXISTS notebooks (
    notebook_id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    notebook_type TEXT DEFAULT 'general',
    description TEXT,
    created_at INTEGER,
    updated_at INTEGER,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS cells (
    cell_id TEXT PRIMARY KEY,
    notebook_id TEXT NOT NULL,
    order_index INTEGER DEFAULT 0,
    week INTEGER DEFAULT 1,
    user_content TEXT,
    ai_content TEXT,
    FOREIGN KEY (notebook_id) REFERENCES notebooks(notebook_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS educational_metadata (
    edu_id SERIAL PRIMARY KEY,
    notebook_id TEXT NOT NULL,
    learning_goal TEXT,
    course_topic TEXT,
    syllabus TEXT,
    roadmap TEXT,
    progress REAL DEFAULT 0.0,
    created_at TEXT,
    FOREIGN KEY (notebook_id) REFERENCES notebooks(notebook_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tasks (
    task_id TEXT PRIMARY KEY,
    notebook_id TEXT NOT NULL,
    week INTEGER NOT NULL,
    day INTEGER NOT NULL,
    order_index INTEGER DEFAULT 0,
    task_description TEXT,
    status TEXT DEFAULT 'pending',
    created_at INTEGER,
    updated_at INTEGER,
    FOREIGN KEY (notebook_id) REFERENCES notebooks(notebook_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS cell_attachments (
    attachment_id TEXT PRIMARY KEY,
    cell_id TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_type TEXT,
    storage_path TEXT,
    created_at INTEGER,
    FOREIGN KEY (cell_id) REFERENCES cells(cell_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS recall_sessions (
    session_id TEXT PRIMARY KEY,
    edu_id INTEGER NOT NULL,
    difficulty TEXT,
    question_count INTEGER,
    average_score REAL,
    created_at TEXT DEFAULT to_char(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS'),
    FOREIGN KEY (edu_id) REFERENCES educational_metadata(edu_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS recall_questions (
    id SERIAL PRIMARY KEY,
    edu_id INTEGER NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    question_type TEXT,
    options TEXT,
    difficulty TEXT,
    session_id TEXT,
    FOREIGN KEY (edu_id) REFERENCES educational_metadata(edu_id) ON DELETE CASCADE,
    FOREIGN KEY (session_id) REFERENCES recall_sessions(session_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS recall_attempts (
    id SERIAL PRIMARY KEY,
    recall_question_id INTEGER NOT NULL,
    user_answer TEXT,
    score REAL,
    feedback TEXT,
    created_at TEXT DEFAULT to_char(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS'),
    FOREIGN KEY (recall_question_id) REFERENCES recall_questions(id) ON DELETE CASCADE
);
