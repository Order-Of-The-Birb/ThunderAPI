CREATE TABLE tokens (
    hash_token TEXT NOT NULL UNIQUE,
    email TEXT PRIMARY KEY ,
    jwt TEXT NOT NULL, -- Includes expiry time as a field
    jwt_expires INTEGER NOT NULL, -- UNIX Timestamp
    token TEXT NOT NULL,
    uidHint INTEGER NOT NULL,
    requests_count INTEGER DEFAULT 0,
    last_used INTEGER NOT NULL, -- UNIX Timestamp
    created_at INTEGER NOT NULL DEFAULT (unixepoch()) -- UNIX Timestamp
);
CREATE TABLE sso_sessions (
    email TEXT PRIMARY KEY REFERENCES tokens(email),
    sid TEXT NOT NULL,
    exp INTEGER NOT NULL -- UNIX timestamp (now + 14 days)
);

CREATE INDEX idx_hashed_token ON tokens(hash_token);
CREATE INDEX idx_last_used ON tokens(last_used);