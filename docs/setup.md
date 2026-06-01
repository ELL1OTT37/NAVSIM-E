# NAVSIM-E setup notes

## Relationship to official splits

| Split | Role |
|-------|------|
| OpenScene `test` | Parent download (logs + sensors) |
| `navtest` | Official NAVSIM filtered test split |
| **NAVSIM-E** | 2364-token subset used in our corruption / collision study |

`scene_filter/navsim-e.yaml` lists all tokens. `manifests/navsim-e_manifest.csv` adds `log_name` and corruption metadata.

## Evaluation with NAVSIM v2

1. Clone [autonomousvision/navsim](https://github.com/autonomousvision/navsim) (v2 / main).
2. Install dependencies and download maps + **test** data.
3. Add this repo’s `navsim-e.yaml` under  
   `navsim/planning/script/config/common/train_test_split/scene_filter/`.
4. Point `navsim_log_path` / sensor paths to your OpenScene tree (or extracted subset).
5. Run metric caching and PDM scoring with  
   `train_test_split.scene_filter=navsim-e`.

Exact shell commands depend on your agent; mirror the upstream `run_metric_caching.sh` / `run_pdm_score` scripts.

## Corrupted sensor blobs

Some tokens use augmented cameras under separate folders (e.g. `sensor_blobs_night`, `sensor_blobs_spatter`). For those scenes, either:

- run agents on the matching corruption path, or  
- use `--src-sensor-blobs` pointing at the corruption-specific root when calling `extract_subset.py`.

Check the `selected_source` / `frame_type` columns in `navsim-e_manifest.csv`.

## Lidar fallback

If a corruption folder has cameras only, pass:

```bash
--src-sensor-blobs-lidar "$OPENSCENE_DATA_ROOT/sensor_blobs" \
--lidar-source-split test
```

## Verify token count

```bash
wc -l manifests/navsim-e_tokens.txt   # expect 2364
```
