# NAVSIM-E dataset composition

## Parent data

NAVSIM-E is a **subset of OpenScene `test`** used by NAVSIM v2. Each entry is one **scene token** (one temporal window), not a full driving log.

## Scene window

Defined in `scene_filter/navsim-e.yaml`:

- `num_history_frames`: 4  
- `num_future_frames`: 10  
- `frame_interval`: 1  
- `has_route`: true  

## Camera mix (2364 tokens)

| Camera data | Share | Count |
|-------------|------:|------:|
| **Processed** (offline corruptions) | **~2/3** | **1576** |
| **Normal** (raw OpenScene test) | **~1/3** | **788** |

All tokens are disjoint. For each scene, **`selected_source`** in the manifest indicates whether to load processed camera trees (`night`, `snow`, `spatter`) or the normal `sensor_blobs/test` path.

Corrupted cameras are offline augmentations of `sensor_blobs/test`; see [setup.md](setup.md#corruption-handling).

## Manifest columns

`manifests/navsim-e_manifest.csv` includes:

- `token`, `log_name` — scene id and parent OpenScene log  
- `selected_source` — camera treatment (`night`, `snow`, `spatter`, or `raw`)  

## What this repo does not ship

- Raw or corrupted sensor files  
- NAVSIM devkit or agent code  
- Corruption generation scripts (maintained separately in our research codebase)
