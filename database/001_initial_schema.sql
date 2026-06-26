-- ArbotFlash universal catalogue foundation
-- PostgreSQL 16+ with PostGIS and ltree

create extension if not exists pgcrypto;
create extension if not exists postgis;
create extension if not exists ltree;

create type verification_status as enum (
  'authoritative_import', 'specialist_import', 'expert_verified',
  'community_submitted', 'ai_assisted_draft', 'unverified',
  'disputed', 'superseded'
);

create type life_status as enum ('extant', 'recently_extinct', 'extinct', 'uncertain');
create type name_status as enum ('accepted', 'synonym', 'historic', 'misapplied', 'common', 'hybrid', 'cultivar');
create type assertion_status as enum ('draft', 'published', 'disputed', 'superseded');

create table source_dataset (
  id uuid primary key default gen_random_uuid(),
  key text not null unique,
  title text not null,
  publisher text,
  homepage_url text,
  licence_code text,
  licence_url text,
  authority_role text not null,
  created_at timestamptz not null default now()
);

create table source_release (
  id uuid primary key default gen_random_uuid(),
  source_dataset_id uuid not null references source_dataset(id),
  release_key text not null,
  issued_on date,
  doi text,
  download_url text,
  imported_at timestamptz,
  immutable_manifest jsonb not null default '{}'::jsonb,
  unique(source_dataset_id, release_key)
);

create table taxon (
  id uuid primary key default gen_random_uuid(),
  canonical_parent_id uuid references taxon(id),
  canonical_rank text not null,
  canonical_scientific_name text not null,
  life_status life_status not null default 'extant',
  lineage_path ltree,
  canonical_source_release_id uuid references source_release(id),
  verification_status verification_status not null default 'unverified',
  last_reviewed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index taxon_parent_idx on taxon(canonical_parent_id);
create index taxon_rank_idx on taxon(canonical_rank);
create index taxon_lineage_gist on taxon using gist(lineage_path);
create index taxon_name_trgm_hint on taxon using btree(lower(canonical_scientific_name));

create table taxon_name (
  id uuid primary key default gen_random_uuid(),
  taxon_id uuid not null references taxon(id) on delete cascade,
  name text not null,
  authorship text,
  status name_status not null,
  language_code text,
  region_code text,
  source_release_id uuid references source_release(id),
  external_record_id text,
  verification_status verification_status not null default 'unverified'
);

create unique index taxon_name_unique_idx on taxon_name(taxon_id, name, status, coalesce(language_code, ''), coalesce(region_code, ''));
create index taxon_name_lookup_idx on taxon_name(lower(name));

create table taxon_external_identifier (
  taxon_id uuid not null references taxon(id) on delete cascade,
  source_dataset_id uuid not null references source_dataset(id),
  external_id text not null,
  external_url text,
  source_release_id uuid references source_release(id),
  primary key(taxon_id, source_dataset_id, external_id)
);

create table taxon_relationship (
  subject_taxon_id uuid not null references taxon(id) on delete cascade,
  predicate text not null,
  object_taxon_id uuid not null references taxon(id) on delete cascade,
  source_release_id uuid references source_release(id),
  verification_status verification_status not null default 'unverified',
  primary key(subject_taxon_id, predicate, object_taxon_id)
);

create table region (
  id uuid primary key default gen_random_uuid(),
  parent_region_id uuid references region(id),
  region_type text not null,
  name text not null,
  code text,
  path ltree,
  geometry geometry(MultiPolygon, 4326),
  source_dataset_id uuid references source_dataset(id)
);

create unique index region_unique_idx on region(region_type, name, coalesce(code, ''));
create index region_parent_idx on region(parent_region_id);
create index region_path_gist on region using gist(path);
create index region_geometry_gist on region using gist(geometry);

create table trait_definition (
  id uuid primary key default gen_random_uuid(),
  key text not null unique,
  label text not null,
  description text,
  data_type text not null check (data_type in ('boolean','text','number','range','option','multi_option','date','season')),
  unit text,
  filterable boolean not null default true,
  multi_valued boolean not null default false,
  applicable_lineages text[] not null default '{}',
  allowed_values jsonb not null default '[]'::jsonb
);

create table taxon_trait_assertion (
  id uuid primary key default gen_random_uuid(),
  taxon_id uuid not null references taxon(id) on delete cascade,
  trait_definition_id uuid not null references trait_definition(id),
  value_json jsonb not null,
  source_dataset_id uuid references source_dataset(id),
  source_release_id uuid references source_release(id),
  citation_text text,
  verification_status verification_status not null default 'unverified',
  assertion_status assertion_status not null default 'draft',
  reviewed_at timestamptz,
  created_at timestamptz not null default now()
);

create index taxon_trait_taxon_idx on taxon_trait_assertion(taxon_id);
create index taxon_trait_definition_idx on taxon_trait_assertion(trait_definition_id);
create index taxon_trait_value_gin on taxon_trait_assertion using gin(value_json);

create table taxon_region_assertion (
  id uuid primary key default gen_random_uuid(),
  taxon_id uuid not null references taxon(id) on delete cascade,
  region_id uuid not null references region(id) on delete cascade,
  occurrence_status text not null default 'present',
  establishment_status text,
  seasonality text,
  confidence numeric(4,3),
  source_dataset_id uuid references source_dataset(id),
  source_release_id uuid references source_release(id),
  verification_status verification_status not null default 'unverified'
);

create unique index taxon_region_unique_idx on taxon_region_assertion(taxon_id, region_id, occurrence_status, coalesce(establishment_status, ''));

create table profile_section (
  id uuid primary key default gen_random_uuid(),
  taxon_id uuid not null references taxon(id) on delete cascade,
  section_key text not null,
  language_code text not null default 'en',
  body_markdown text not null,
  source_dataset_id uuid references source_dataset(id),
  source_revision text,
  licence_code text,
  verification_status verification_status not null default 'unverified',
  assertion_status assertion_status not null default 'draft',
  last_reviewed_at timestamptz,
  unique(taxon_id, section_key, language_code)
);

create table media_asset (
  id uuid primary key default gen_random_uuid(),
  storage_key text,
  original_url text not null,
  media_type text not null default 'image',
  title text,
  creator text,
  source_page_url text,
  licence_code text not null,
  licence_url text,
  captured_at timestamptz,
  latitude double precision,
  longitude double precision,
  locality text,
  verification_status verification_status not null default 'unverified',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table media_taxon (
  media_asset_id uuid not null references media_asset(id) on delete cascade,
  taxon_id uuid not null references taxon(id) on delete cascade,
  category text not null,
  caption text,
  diagnostic_notes text,
  is_primary boolean not null default false,
  primary key(media_asset_id, taxon_id, category)
);

create table reconciliation_queue (
  taxon_id uuid not null references taxon(id) on delete cascade,
  source_dataset_id uuid not null references source_dataset(id),
  searched_name text not null,
  status text not null default 'pending',
  proposed_external_id text,
  proposed_scientific_name text,
  proposed_rank text,
  confidence numeric(4,3),
  notes text,
  checked_at timestamptz,
  primary key(taxon_id, source_dataset_id)
);

create index reconciliation_status_idx on reconciliation_queue(status);

create table review_decision (
  id uuid primary key default gen_random_uuid(),
  taxon_id uuid not null references taxon(id) on delete cascade,
  source_dataset_id uuid not null references source_dataset(id),
  decision text not null,
  reviewer text not null,
  rationale text,
  previous_status text,
  new_status text,
  decided_at timestamptz not null default now()
);

create index review_decision_taxon_idx on review_decision(taxon_id, decided_at desc);

create table audit_event (
  id uuid primary key default gen_random_uuid(),
  actor text not null,
  action text not null,
  entity_type text not null,
  entity_id text not null,
  before_state jsonb,
  after_state jsonb,
  created_at timestamptz not null default now()
);

create index audit_event_entity_idx on audit_event(entity_type, entity_id, created_at desc);

create table saved_filter_stack (
  id uuid primary key default gen_random_uuid(),
  user_id uuid,
  title text not null,
  filters jsonb not null,
  taxonomy_release_id uuid references source_release(id),
  is_frozen boolean not null default false,
  frozen_taxon_ids uuid[],
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table deck (
  id uuid primary key default gen_random_uuid(),
  user_id uuid,
  title text not null,
  filter_stack_id uuid references saved_filter_stack(id),
  selection_mode text not null,
  question_modes text[] not null default '{}',
  settings jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table deck_taxon (
  deck_id uuid not null references deck(id) on delete cascade,
  taxon_id uuid not null references taxon(id),
  position integer,
  primary key(deck_id, taxon_id)
);

create table study_session (
  id uuid primary key default gen_random_uuid(),
  user_id uuid,
  deck_id uuid references deck(id),
  started_at timestamptz not null default now(),
  completed_at timestamptz
);

create table study_answer (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references study_session(id) on delete cascade,
  taxon_id uuid not null references taxon(id),
  question_mode text not null,
  shown_media_asset_id uuid references media_asset(id),
  answer_text text,
  correct boolean not null,
  response_ms integer,
  answered_at timestamptz not null default now()
);

create table taxon_mastery (
  user_id uuid not null,
  taxon_id uuid not null references taxon(id) on delete cascade,
  attempts integer not null default 0,
  correct_attempts integer not null default 0,
  mastery_score numeric(5,4) not null default 0,
  last_studied_at timestamptz,
  next_review_at timestamptz,
  primary key(user_id, taxon_id)
);
