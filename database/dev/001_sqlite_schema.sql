PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS app_metadata (
  key TEXT PRIMARY KEY,
  value_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS source_dataset (
  id TEXT PRIMARY KEY,
  key TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  publisher TEXT,
  homepage_url TEXT,
  licence_code TEXT,
  licence_url TEXT,
  authority_role TEXT NOT NULL,
  enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
  notes TEXT
);

CREATE TABLE IF NOT EXISTS source_release (
  id TEXT PRIMARY KEY,
  source_dataset_id TEXT NOT NULL REFERENCES source_dataset(id),
  release_key TEXT NOT NULL,
  issued_on TEXT,
  doi TEXT,
  download_url TEXT,
  imported_at TEXT,
  immutable_manifest_json TEXT NOT NULL DEFAULT '{}',
  UNIQUE(source_dataset_id, release_key)
);

CREATE TABLE IF NOT EXISTS taxon (
  id TEXT PRIMARY KEY,
  canonical_scientific_name TEXT NOT NULL,
  canonical_rank TEXT NOT NULL,
  life_status TEXT NOT NULL DEFAULT 'extant',
  canonical_source_release_id TEXT REFERENCES source_release(id),
  verification_status TEXT NOT NULL DEFAULT 'unverified',
  source_record_index INTEGER,
  last_reviewed_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS taxon_name (
  id TEXT PRIMARY KEY,
  taxon_id TEXT NOT NULL REFERENCES taxon(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  authorship TEXT,
  status TEXT NOT NULL,
  language_code TEXT,
  region_code TEXT,
  source_release_id TEXT REFERENCES source_release(id),
  external_record_id TEXT,
  verification_status TEXT NOT NULL DEFAULT 'unverified'
);
CREATE UNIQUE INDEX IF NOT EXISTS taxon_name_unique_idx
  ON taxon_name(taxon_id, name, status, IFNULL(language_code, ''), IFNULL(region_code, ''));
CREATE INDEX IF NOT EXISTS taxon_name_lookup_idx ON taxon_name(name COLLATE NOCASE);

CREATE TABLE IF NOT EXISTS taxon_classification (
  taxon_id TEXT NOT NULL REFERENCES taxon(id) ON DELETE CASCADE,
  rank TEXT NOT NULL,
  name TEXT NOT NULL,
  source_release_id TEXT REFERENCES source_release(id),
  verification_status TEXT NOT NULL DEFAULT 'unverified',
  PRIMARY KEY(taxon_id, rank)
);
CREATE INDEX IF NOT EXISTS classification_rank_name_idx
  ON taxon_classification(rank, name COLLATE NOCASE);

CREATE TABLE IF NOT EXISTS taxon_external_identifier (
  taxon_id TEXT NOT NULL REFERENCES taxon(id) ON DELETE CASCADE,
  source_dataset_id TEXT NOT NULL REFERENCES source_dataset(id),
  external_id TEXT NOT NULL,
  external_url TEXT,
  source_release_id TEXT REFERENCES source_release(id),
  PRIMARY KEY(taxon_id, source_dataset_id, external_id)
);

CREATE TABLE IF NOT EXISTS trait_definition (
  key TEXT PRIMARY KEY,
  label TEXT NOT NULL,
  group_name TEXT NOT NULL,
  data_type TEXT NOT NULL DEFAULT 'option',
  filterable INTEGER NOT NULL DEFAULT 1 CHECK (filterable IN (0, 1)),
  multi_valued INTEGER NOT NULL DEFAULT 0 CHECK (multi_valued IN (0, 1)),
  applicable_lineages_json TEXT NOT NULL DEFAULT '[]',
  allowed_values_json TEXT NOT NULL DEFAULT '[]',
  sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS taxon_trait_assertion (
  id TEXT PRIMARY KEY,
  taxon_id TEXT NOT NULL REFERENCES taxon(id) ON DELETE CASCADE,
  trait_key TEXT NOT NULL REFERENCES trait_definition(key),
  value_json TEXT NOT NULL,
  source_release_id TEXT REFERENCES source_release(id),
  citation_text TEXT,
  verification_status TEXT NOT NULL DEFAULT 'unverified',
  assertion_status TEXT NOT NULL DEFAULT 'draft',
  reviewed_at TEXT,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS taxon_trait_taxon_idx ON taxon_trait_assertion(taxon_id);
CREATE INDEX IF NOT EXISTS taxon_trait_key_idx ON taxon_trait_assertion(trait_key);

CREATE TABLE IF NOT EXISTS profile_section (
  id TEXT PRIMARY KEY,
  taxon_id TEXT NOT NULL REFERENCES taxon(id) ON DELETE CASCADE,
  section_key TEXT NOT NULL,
  language_code TEXT NOT NULL DEFAULT 'en',
  body_markdown TEXT NOT NULL,
  source_release_id TEXT REFERENCES source_release(id),
  source_revision TEXT,
  licence_code TEXT,
  verification_status TEXT NOT NULL DEFAULT 'unverified',
  assertion_status TEXT NOT NULL DEFAULT 'draft',
  last_reviewed_at TEXT,
  UNIQUE(taxon_id, section_key, language_code)
);

CREATE TABLE IF NOT EXISTS region (
  id TEXT PRIMARY KEY,
  parent_region_id TEXT REFERENCES region(id),
  region_type TEXT NOT NULL,
  name TEXT NOT NULL,
  code TEXT,
  source_dataset_id TEXT REFERENCES source_dataset(id)
);

CREATE UNIQUE INDEX IF NOT EXISTS region_unique_idx
  ON region(region_type, name, IFNULL(code, ''));

CREATE TABLE IF NOT EXISTS taxon_region_assertion (
  id TEXT PRIMARY KEY,
  taxon_id TEXT NOT NULL REFERENCES taxon(id) ON DELETE CASCADE,
  region_id TEXT NOT NULL REFERENCES region(id) ON DELETE CASCADE,
  occurrence_status TEXT NOT NULL DEFAULT 'present',
  establishment_status TEXT,
  seasonality TEXT,
  confidence REAL,
  source_release_id TEXT REFERENCES source_release(id),
  verification_status TEXT NOT NULL DEFAULT 'unverified'
);

CREATE TABLE IF NOT EXISTS media_asset (
  id TEXT PRIMARY KEY,
  storage_key TEXT,
  original_url TEXT NOT NULL,
  media_type TEXT NOT NULL DEFAULT 'image',
  title TEXT,
  creator TEXT,
  source_page_url TEXT,
  licence_code TEXT NOT NULL,
  licence_url TEXT,
  captured_at TEXT,
  latitude REAL,
  longitude REAL,
  locality TEXT,
  verification_status TEXT NOT NULL DEFAULT 'unverified',
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS media_taxon (
  media_asset_id TEXT NOT NULL REFERENCES media_asset(id) ON DELETE CASCADE,
  taxon_id TEXT NOT NULL REFERENCES taxon(id) ON DELETE CASCADE,
  category TEXT NOT NULL,
  caption TEXT,
  diagnostic_notes TEXT,
  is_primary INTEGER NOT NULL DEFAULT 0 CHECK (is_primary IN (0, 1)),
  PRIMARY KEY(media_asset_id, taxon_id, category)
);

CREATE TABLE IF NOT EXISTS source_citation (
  id TEXT PRIMARY KEY,
  taxon_id TEXT REFERENCES taxon(id) ON DELETE CASCADE,
  record_type TEXT NOT NULL,
  record_id TEXT NOT NULL,
  source_release_id TEXT REFERENCES source_release(id),
  citation_text TEXT NOT NULL,
  source_url TEXT,
  retrieved_at TEXT,
  licence_code TEXT
);

CREATE TABLE IF NOT EXISTS reconciliation_queue (
  taxon_id TEXT NOT NULL REFERENCES taxon(id) ON DELETE CASCADE,
  source_dataset_id TEXT NOT NULL REFERENCES source_dataset(id),
  searched_name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  proposed_external_id TEXT,
  proposed_scientific_name TEXT,
  proposed_rank TEXT,
  confidence REAL,
  notes TEXT,
  checked_at TEXT,
  PRIMARY KEY(taxon_id, source_dataset_id)
);
CREATE INDEX IF NOT EXISTS reconciliation_status_idx ON reconciliation_queue(status);

CREATE TABLE IF NOT EXISTS review_decision (
  id TEXT PRIMARY KEY,
  taxon_id TEXT NOT NULL REFERENCES taxon(id) ON DELETE CASCADE,
  source_dataset_id TEXT NOT NULL REFERENCES source_dataset(id),
  decision TEXT NOT NULL,
  reviewer TEXT NOT NULL,
  rationale TEXT,
  previous_status TEXT,
  new_status TEXT,
  decided_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS review_decision_taxon_idx ON review_decision(taxon_id, decided_at);

CREATE TABLE IF NOT EXISTS audit_event (
  id TEXT PRIMARY KEY,
  actor TEXT NOT NULL,
  action TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  before_json TEXT,
  after_json TEXT,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS audit_event_entity_idx ON audit_event(entity_type, entity_id, created_at);

-- Read-optimised projection. The normalised tables remain the source of truth.
CREATE TABLE IF NOT EXISTS taxon_search_projection (
  taxon_id TEXT PRIMARY KEY REFERENCES taxon(id) ON DELETE CASCADE,
  scientific_name TEXT NOT NULL,
  common_name TEXT NOT NULL,
  domain_name TEXT,
  kingdom_name TEXT,
  phylum_name TEXT,
  class_name TEXT,
  order_name TEXT,
  family_name TEXT,
  genus_name TEXT,
  life_status TEXT NOT NULL,
  verification_status TEXT NOT NULL,
  source_pack TEXT,
  reconciliation_status TEXT,
  profile_status TEXT,
  image_status TEXT,
  traits_json TEXT NOT NULL DEFAULT '{}',
  searchable_text TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS projection_scientific_idx ON taxon_search_projection(scientific_name COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS projection_common_idx ON taxon_search_projection(common_name COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS projection_family_idx ON taxon_search_projection(family_name COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS projection_genus_idx ON taxon_search_projection(genus_name COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS projection_kingdom_idx ON taxon_search_projection(kingdom_name COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS projection_status_idx ON taxon_search_projection(life_status, verification_status);
