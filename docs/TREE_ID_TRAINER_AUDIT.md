# Finished Tree ID Trainer audit

Source: user-supplied `Tree_ID_Trainer_v15_23_VERIFIED_FULL_GITHUB_UPLOAD(1)(1).zip`

SHA-256: `b94715dd289d17ecf6415121565148cbd671f608a04b531606adf72be55f0b55`

## Confirmed contents

- 44 files
- 6,847,080 bytes uncompressed
- Vercel deployment configuration
- One main `public/index.html` containing the interface, styles, application logic and seed taxon list
- Offline PWA manifest and service worker
- Four complete visual themes with six assets each
- Serverless AI command, AI speech and visit-counter endpoints

## Seed dataset

- 80 records
- 80 unique scientific names
- 35 genera
- 21 families
- 38 records in Myrtaceae
- One repeated common name: `Flooded Gum`, referring to both `Eucalyptus grandis` and `Eucalyptus rudis`

Each built-in record contains only:

- Scientific/binomial name
- Common name
- Family

The finished site does not contain species-specific photographs or detailed species profiles. Its image files are application/theme artwork. ArbotFlash therefore needs new sourced records for morphology, distribution, ecology, chemistry, specimens, media and citations.

## Working features identified

- Common name → binomial flashcards
- Binomial → common name flashcards
- Genus → family flashcards
- Family → genus flashcards
- Family filter
- Previous card control
- Family/genus matching game
- Binomial/common-name matching game
- Scores, moves and streaks
- Browser/device text-to-speech
- Optional server-generated speech profiles with local clip caching
- Microphone and speech-recognition command input
- AI command planner with a restricted action schema
- Add, edit, remove, import and export functions
- Undo for AI changes
- Tutorial
- Four themes
- Offline PWA and install prompt
- Local and optional global visit counters

## Original browser-storage namespaces

The finished trainer uses keys beginning with `tree-id-trainer-`, including data, statistics, speech, AI undo/log/cache, theme, visits and install-prompt state.

ArbotFlash uses only `arbotflash.*` namespaces. It also has a distinct service-worker cache. Running both applications on the same device cannot overwrite the trainer's local data.

## Reuse decision

### Reuse as behaviour/reference

- Fast card interaction
- Four name/taxonomy question directions
- Previous/next navigation
- Answer scoring and streak model
- Speech controls
- Import/export workflow concepts
- Tutorial structure
- Theme artwork, subject to confirming ownership/licensing
- Offline-first expectations

### Rebuild as structured modules

- Taxon storage
- Filtering
- Search
- Deck generation
- Detailed profiles
- Species image records
- Sources and citations
- Accounts and synced progress
- Taxonomy updates
- Regional packs
- Administration and moderation

### Do not migrate as production architecture

- One-file application structure
- Entire dataset embedded in HTML
- Tree-specific AI action names
- Browser-only editing as the authoritative global data store
- One global cache containing the whole future catalogue

## Version-label note

The supplied filename identifies the package as v15.23, while internal files contain older labels such as v15.9.1, package version 15.0.0 and service-worker cache suffix v23. ArbotFlash records the source by upload hash and filename rather than assuming those internal labels are perfectly synchronised.
