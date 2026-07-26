PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS registry_releases (
  id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL,
  source_version TEXT NOT NULL,
  source_dataset_id TEXT NOT NULL DEFAULT '',
  source_url TEXT NOT NULL,
  published_at TEXT,
  retrieved_at TEXT NOT NULL,
  archive_sha256 TEXT NOT NULL,
  licence TEXT NOT NULL DEFAULT '',
  citation TEXT NOT NULL DEFAULT '',
  record_count INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'staged' CHECK (status IN ('staged','reviewed','published','rejected')),
  UNIQUE(source_id, source_version, archive_sha256)
);

CREATE TABLE IF NOT EXISTS taxon_concepts (
  id TEXT PRIMARY KEY,
  canonical_name TEXT NOT NULL,
  canonical_authorship TEXT NOT NULL DEFAULT '',
  rank TEXT NOT NULL,
  kingdom TEXT NOT NULL DEFAULT 'Plantae',
  family TEXT NOT NULL DEFAULT '',
  genus TEXT NOT NULL DEFAULT '',
  parent_concept_id TEXT REFERENCES taxon_concepts(id),
  arboreal_status TEXT NOT NULL DEFAULT 'unknown' CHECK (arboreal_status IN ('tree','tree-like','not-tree','unknown')),
  lifecycle_status TEXT NOT NULL DEFAULT 'active' CHECK (lifecycle_status IN ('active','merged','deprecated')),
  preferred_backbone TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_taxon_concepts_name ON taxon_concepts(canonical_name);
CREATE INDEX IF NOT EXISTS idx_taxon_concepts_family ON taxon_concepts(family);
CREATE INDEX IF NOT EXISTS idx_taxon_concepts_genus ON taxon_concepts(genus);
CREATE INDEX IF NOT EXISTS idx_taxon_concepts_arboreal ON taxon_concepts(arboreal_status);

CREATE TABLE IF NOT EXISTS source_taxa (
  release_id TEXT NOT NULL REFERENCES registry_releases(id) ON DELETE CASCADE,
  source_taxon_id TEXT NOT NULL,
  scientific_name TEXT NOT NULL,
  authorship TEXT NOT NULL DEFAULT '',
  rank TEXT NOT NULL DEFAULT '',
  taxonomic_status TEXT NOT NULL DEFAULT '',
  nomenclatural_status TEXT NOT NULL DEFAULT '',
  accepted_source_taxon_id TEXT NOT NULL DEFAULT '',
  parent_source_taxon_id TEXT NOT NULL DEFAULT '',
  kingdom TEXT NOT NULL DEFAULT '',
  family TEXT NOT NULL DEFAULT '',
  genus TEXT NOT NULL DEFAULT '',
  name_according_to TEXT NOT NULL DEFAULT '',
  dataset_name TEXT NOT NULL DEFAULT '',
  raw_json TEXT NOT NULL DEFAULT '{}',
  PRIMARY KEY (release_id, source_taxon_id)
);

CREATE INDEX IF NOT EXISTS idx_source_taxa_scientific_name ON source_taxa(scientific_name);
CREATE INDEX IF NOT EXISTS idx_source_taxa_accepted ON source_taxa(release_id, accepted_source_taxon_id);
CREATE INDEX IF NOT EXISTS idx_source_taxa_parent ON source_taxa(release_id, parent_source_taxon_id);

CREATE TABLE IF NOT EXISTS concept_mappings (
  concept_id TEXT NOT NULL REFERENCES taxon_concepts(id) ON DELETE CASCADE,
  release_id TEXT NOT NULL,
  source_taxon_id TEXT NOT NULL,
  relationship TEXT NOT NULL CHECK (relationship IN ('accepted','synonym','alternative','misapplied','unresolved')),
  confidence REAL NOT NULL DEFAULT 0.0 CHECK (confidence >= 0.0 AND confidence <= 1.0),
  review_status TEXT NOT NULL DEFAULT 'machine-proposed' CHECK (review_status IN ('machine-proposed','reviewed','rejected')),
  reviewer TEXT NOT NULL DEFAULT '',
  reviewed_at TEXT,
  notes TEXT NOT NULL DEFAULT '',
  PRIMARY KEY (concept_id, release_id, source_taxon_id),
  FOREIGN KEY (release_id, source_taxon_id) REFERENCES source_taxa(release_id, source_taxon_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_concept_mappings_source ON concept_mappings(release_id, source_taxon_id);

CREATE TABLE IF NOT EXISTS taxon_names (
  id TEXT PRIMARY KEY,
  concept_id TEXT NOT NULL REFERENCES taxon_concepts(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  authorship TEXT NOT NULL DEFAULT '',
  name_type TEXT NOT NULL CHECK (name_type IN ('accepted','synonym','historic','vernacular','trade','misapplied')),
  language TEXT NOT NULL DEFAULT '',
  region_code TEXT NOT NULL DEFAULT '',
  source_id TEXT NOT NULL DEFAULT '',
  release_id TEXT REFERENCES registry_releases(id),
  source_name_id TEXT NOT NULL DEFAULT '',
  is_preferred INTEGER NOT NULL DEFAULT 0 CHECK (is_preferred IN (0,1)),
  notes TEXT NOT NULL DEFAULT '',
  UNIQUE(concept_id, name, authorship, name_type, language, region_code, source_id)
);

CREATE INDEX IF NOT EXISTS idx_taxon_names_name ON taxon_names(name);
CREATE INDEX IF NOT EXISTS idx_taxon_names_concept ON taxon_names(concept_id);
CREATE INDEX IF NOT EXISTS idx_taxon_names_region ON taxon_names(region_code, is_preferred);

CREATE TABLE IF NOT EXISTS regional_treatments (
  concept_id TEXT NOT NULL REFERENCES taxon_concepts(id) ON DELETE CASCADE,
  region_code TEXT NOT NULL,
  authority_id TEXT NOT NULL,
  accepted_name TEXT NOT NULL,
  accepted_authorship TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'accepted',
  source_url TEXT NOT NULL DEFAULT '',
  release_id TEXT REFERENCES registry_releases(id),
  review_status TEXT NOT NULL DEFAULT 'machine-proposed' CHECK (review_status IN ('machine-proposed','reviewed','rejected')),
  notes TEXT NOT NULL DEFAULT '',
  PRIMARY KEY (concept_id, region_code, authority_id)
);

CREATE TABLE IF NOT EXISTS trait_assertions (
  id TEXT PRIMARY KEY,
  concept_id TEXT NOT NULL REFERENCES taxon_concepts(id) ON DELETE CASCADE,
  trait TEXT NOT NULL,
  value TEXT NOT NULL,
  unit TEXT NOT NULL DEFAULT '',
  region_code TEXT NOT NULL DEFAULT '',
  source_id TEXT NOT NULL,
  release_id TEXT REFERENCES registry_releases(id),
  evidence_url TEXT NOT NULL DEFAULT '',
  review_status TEXT NOT NULL DEFAULT 'machine-proposed' CHECK (review_status IN ('machine-proposed','reviewed','rejected')),
  notes TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_trait_assertions_concept ON trait_assertions(concept_id, trait);

CREATE TABLE IF NOT EXISTS taxonomy_events (
  id TEXT PRIMARY KEY,
  detected_at TEXT NOT NULL,
  source_id TEXT NOT NULL,
  previous_release_id TEXT REFERENCES registry_releases(id),
  current_release_id TEXT REFERENCES registry_releases(id),
  event_type TEXT NOT NULL CHECK (event_type IN ('new-name','new-taxon','accepted-name-change','synonymy-change','rank-change','parent-change','status-change','source-release-change')),
  concept_id TEXT REFERENCES taxon_concepts(id),
  previous_value TEXT NOT NULL DEFAULT '',
  current_value TEXT NOT NULL DEFAULT '',
  evidence_json TEXT NOT NULL DEFAULT '{}',
  review_status TEXT NOT NULL DEFAULT 'unreviewed' CHECK (review_status IN ('unreviewed','reviewed','accepted','rejected')),
  reviewer TEXT NOT NULL DEFAULT '',
  reviewed_at TEXT,
  notes TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_taxonomy_events_review ON taxonomy_events(review_status, detected_at);

CREATE TABLE IF NOT EXISTS taxon_search_projection (
  concept_id TEXT PRIMARY KEY REFERENCES taxon_concepts(id) ON DELETE CASCADE,
  accepted_name TEXT NOT NULL,
  accepted_authorship TEXT NOT NULL DEFAULT '',
  common_name TEXT NOT NULL DEFAULT '',
  aliases TEXT NOT NULL DEFAULT '',
  family TEXT NOT NULL DEFAULT '',
  genus TEXT NOT NULL DEFAULT '',
  rank TEXT NOT NULL DEFAULT '',
  arboreal_status TEXT NOT NULL DEFAULT 'unknown',
  region_codes TEXT NOT NULL DEFAULT '',
  authority_profile TEXT NOT NULL DEFAULT 'global',
  profile_status TEXT NOT NULL DEFAULT 'shell',
  updated_at TEXT NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS taxon_search_fts USING fts5(
  accepted_name,
  common_name,
  aliases,
  family,
  genus,
  content='taxon_search_projection',
  content_rowid='rowid',
  tokenize='unicode61 remove_diacritics 2'
);

CREATE TRIGGER IF NOT EXISTS taxon_search_projection_ai AFTER INSERT ON taxon_search_projection BEGIN
  INSERT INTO taxon_search_fts(rowid, accepted_name, common_name, aliases, family, genus)
  VALUES (new.rowid, new.accepted_name, new.common_name, new.aliases, new.family, new.genus);
END;

CREATE TRIGGER IF NOT EXISTS taxon_search_projection_ad AFTER DELETE ON taxon_search_projection BEGIN
  INSERT INTO taxon_search_fts(taxon_search_fts, rowid, accepted_name, common_name, aliases, family, genus)
  VALUES ('delete', old.rowid, old.accepted_name, old.common_name, old.aliases, old.family, old.genus);
END;

CREATE TRIGGER IF NOT EXISTS taxon_search_projection_au AFTER UPDATE ON taxon_search_projection BEGIN
  INSERT INTO taxon_search_fts(taxon_search_fts, rowid, accepted_name, common_name, aliases, family, genus)
  VALUES ('delete', old.rowid, old.accepted_name, old.common_name, old.aliases, old.family, old.genus);
  INSERT INTO taxon_search_fts(rowid, accepted_name, common_name, aliases, family, genus)
  VALUES (new.rowid, new.accepted_name, new.common_name, new.aliases, new.family, new.genus);
END;
