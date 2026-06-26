# Tree ID Trainer → ArbotFlash migration map

| Finished trainer element | ArbotFlash destination | v0.2 state |
|---|---|---|
| `BUILTIN` array | Seed import and future `taxon`/`taxon_name` tables | Imported: 80/80 |
| Binomial | Canonical scientific name plus source assertion | Imported |
| Common name | Vernacular taxon name | Imported |
| Family | Taxonomic lineage assertion | Imported, reconciliation pending |
| Derived genus | Taxonomic lineage assertion | Imported from first name token |
| Flashcard modes | Study-engine question modes | Four modes working |
| Family filter | General stacked-filter engine | Replaced by reusable taxonomy filters |
| Saved stats | Per-taxon progress and future synced mastery | Local v0.2 progress working |
| Previous card | Shared card navigator | Working |
| Device TTS | Speech adapter | Working in browser |
| Server AI speech | Optional speech service | Deferred; original endpoint preserved only in reference source |
| Matching games | Study-engine game modes | Planned after core card/profile slice |
| AI edit commands | Admin/user command layer | Deferred and must use universal `taxon`, not `tree`, actions |
| CSV import/export | Staging import/export services | Importer upgraded to read ZIP, HTML or JSON |
| Theme artwork | Optional ArbotFlash themes | Preserved in read-only reference; integration pending licence confirmation |
| PWA cache | Versioned application shell plus selected packs | Seed pack cached separately |
| Main HTML monolith | Modular application/API/database | Not carried forward |

## Import policy

The migration is intentionally lossless for the three real taxon fields present in the source. It does not invent class, order, range, morphology or conservation data. Empty fields are enriched later from pinned authoritative releases and reviewed sources.
