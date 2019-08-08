
CREATE TABLE cdx (
    url                 TEXT NOT NULL CHECK (octet_length(url) >= 1),
    datetime            TEXT NOT NULL CHECK (octet_length(datetime) = 14),
    sha1hex             TEXT NOT NULL CHECK (octet_length(sha1hex) = 40),
    cdx_sha1hex         TEXT CHECK (octet_length(cdx_sha1hex) = 40),
    mimetype            TEXT CHECK (octet_length(mimetype) >= 1),
    warc_path           TEXT CHECK (octet_length(warc_path) >= 1),
    warc_offset         BIGINT,
    row_created         TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY(url, datetime)
);
CREATE INDEX cdx_sha1hex_idx ON cdx(sha1hex);
CREATE INDEX cdx_row_created_idx ON cdx(row_created);

CREATE TABLE file_meta (
    sha1hex             TEXT PRIMARY KEY CHECK (octet_length(sha1hex) = 40),
    sha256hex           TEXT CHECK (octet_length(sha256hex) = 64),
    md5hex              TEXT CHECK (octet_length(md5hex) = 32),
    size_bytes          BIGINT,
    mimetype            TEXT CHECK (octet_length(mimetype) >= 1)
);

CREATE TABLE fatcat_file (
    sha1hex             TEXT PRIMARY KEY CHECK (octet_length(sha1hex) = 40),
    file_ident          TEXT CHECK (octet_length(file_ident) = 26),
    first_release_ident TEXT CHECK (octet_length(first_release_ident) = 26)
);

CREATE TABLE petabox (
    item                TEXT NOT NULL CHECK (octet_length(item) >= 1),
    path                TEXT NOT NULL CHECK (octet_length(path) >= 1),
    sha1hex             TEXT NOT NULL CHECK (octet_length(sha1hex) = 40),
    PRIMARY KEY(item, path)
);
CREATE INDEX petabox_sha1hex_idx ON petabox(sha1hex);

CREATE TABLE grobid (
    sha1hex             TEXT PRIMARY KEY CHECK (octet_length(sha1hex) = 40),
    updated             TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    grobid_version      TEXT NOT NULL CHECK (octet_length(grobid_version) >= 1),
    status_code         INT NOT NULL,
    status              TEXT CHECK (octet_length(status) >= 1),
    fatcat_release      TEXT CHECK (octet_length(fatcat_release) = 26),
    metadata            JSONB
);
-- CREATE INDEX grobid_fatcat_release_idx ON grobid(fatcat_release);

CREATE TABLE shadow (
    sha1hex             TEXT NOT NULL CHECK (octet_length(sha1hex) = 40),
    shadow_corpus       TEXT NOT NULL CHECK (octet_length(shadow_corpus) >= 1),
    shadow_id           TEXT CHECK (octet_length(shadow_id) >= 1),
    doi                 TEXT CHECK (octet_length(doi) >= 1),
    pmid                TEXT CHECK (octet_length(pmid) >= 1),
    isbn13              TEXT CHECK (octet_length(isbn13) >= 1),
    PRIMARY KEY(sha1hex, shadow_corpus)
);
