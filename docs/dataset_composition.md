# NAVSIM-E dataset composition

## Parent data

NAVSIM-E is a **subset of OpenScene `test`** used by NAVSIM v2. Each entry is one **scene token** (one temporal window), not a full driving log.

## Scene window

Defined in `scene_filter/navsim-e.yaml`:

- `num_history_frames`: 4  
- `num_future_frames`: 10  
- `frame_interval`: 1  
- `has_route`: true  

## Selection (2364 tokens)

NAVSIM-E is built as **~2/3 processed + ~1/3 normal** cameras:

| Camera data | Count | `source_dataset` pools |
|-------------|------:|------------------------|
| **Processed** (offline corruptions) | **1576** | `extreme_merged` (788) + `processed_random` (788) |
| **Normal** (raw OpenScene test) | **788** | `raw_random` (788) |

The three pools are merged with **no duplicate tokens** (`source_dataset` column):

| `source_dataset` | Count | Description |
|------------------|------:|-------------|
| `extreme_merged` | 788 | Collision- / difficulty-focused scenarios (processed cameras) |
| `processed_random` | 788 | Random test sample with processed cameras |
| `raw_random` | 788 | Random test sample with normal OpenScene cameras (`selected_source=raw`) |

## Corruption label per scene

For **processed** scenes, `selected_source` names the camera tree (`night`, `snow`, or `spatter`). For **normal** scenes it is `raw`. Use `manifests/navsim-e_manifest.csv` for the exact label of each token.

Corrupted cameras are offline augmentations of `sensor_blobs/test`; see [setup.md](setup.md#corruption-handling).

## Manifest columns

`manifests/navsim-e_manifest.csv` includes:

- `token`, `log_name` — scene id and parent OpenScene log  
- `selected_source`, `source_dataset` — corruption type and selection pool  
- `no_at_fault_collisions`, `score`, … — optional PDM / filtering metadata when available  

## What this repo does not ship

- Raw or corrupted sensor files  
- NAVSIM devkit or agent code  
- Corruption generation scripts (maintained separately in our research codebase)
