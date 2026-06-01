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

The benchmark merges **three** scenario pools of **788** tokens each (`source_dataset` column):

| `source_dataset` | Count | Description |
|------------------|------:|-------------|
| `extreme_merged` | 788 | Collision- / difficulty-focused scenarios from merged extreme subsets |
| `processed_random` | 788 | Randomly sampled test tokens paired with **processed** corruptions |
| `raw_random` | 788 | Randomly sampled test tokens using **raw** OpenScene cameras |

## Corruption label per scene

The `selected_source` column indicates which **camera** tree to use (not the selection pool above):

| `selected_source` | Count |
|-------------------|------:|
| `spatter` | 948 |
| `raw` | 788 |
| `snow` | 406 |
| `night` | 222 |

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
