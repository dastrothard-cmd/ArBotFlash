from pathlib import Path
import json, sqlite3, zipfile
ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'database/dev/arbotflash-dev.sqlite3'
with sqlite3.connect(DB) as c:
    taxa=c.execute('select count(*) from taxon').fetchone()[0]
    media=c.execute('select count(*) from media_asset where storage_key is not null').fetchone()[0]
    enriched=c.execute("select count(*) from taxon_search_projection where profile_status != 'Seed shell only'").fetchone()[0]
    shells=c.execute("select count(*) from taxon_search_projection where profile_status = 'Seed shell only'").fetchone()[0]
    schema=json.loads(c.execute("select value_json from app_metadata where key='schema_version'").fetchone()[0])
    assert taxa==80 and media>=60 and enriched>=60 and shells<=20
    assert schema in {'0.10.0','0.11.0','0.12.0'}
manifest=json.loads((ROOT/'packs/tree-id-80/manifest.json').read_text())
assert manifest['coverage']['taxonCount']==80
assert manifest['coverage']['enrichedTaxa']>=60
assert manifest['coverage']['profileShells']<=20
assert manifest['coverage']['localMediaCount']>=60
archive=ROOT/'packs/tree-id-80'/manifest['archiveFile']
with zipfile.ZipFile(archive) as z:
    assert len([n for n in z.namelist() if '/media/' in n and n.endswith('.jpg')])>=60
print('ArbotFlash v0.10 compatibility baseline passed: at least 60 enriched profiles and local images retained.')
