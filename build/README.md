# How the website is built

`website/index.html` is one self-contained page. It is generated. Don't edit it by hand: change the files here and rebuild.

```
python build/inject.py
```

The script fills the placeholders in `site_template.html` with:

| Placeholder | Comes from |
|---|---|
| `__DATA__` | the area list in `Infosys_9km_Area_Map.html` |
| `__BORDERS__`, `__VILLAGES__` | `data/borders_final.json`, `data/villages_final.json` (official revenue-village borders) |
| `__POIS__` | `places/pois.json`: metro, offices, schools, hospitals, parks, restaurants, landmarks, ORR exits |
| `__ROADS__` | `roads/approach.json`: approach road and route to the main road for every map pin (traffic fields are dropped) |
| `__PRELOAD__` | the built-in area CSVs in `area_property_lists/` |

## Refreshing the source data (only when needed)

All map data is from OpenStreetMap, fetched through the Overpass API (https://overpass-api.de).

- **Places:**
  1. Run `places/q.overpassql` and save the result as `places/osm.json`.
  2. Run `places/q2.overpassql` and save the result as `places/osm2.json`.
  3. In `places/`, run `python build_pois.py`.
- **Roads:**
  1. Run `roads/q_roads.overpassql` and save the result as `roads/roads.json` (about 12 MB; kept out of git).
  2. Run `roads/q_names.overpassql` and save the result as `roads/names.json`.
  3. In `roads/`, run `python roads.py`. It reads the listing CSVs and writes `approach.json`.

Run `python build/inject.py` again after either step.
