# NAVSIM-E setup notes

## Relationship to official splits

| Split | Role |
|-------|------|
| OpenScene `test` | Parent download (logs + sensors) |
| `navtest` | Official NAVSIM filtered test split |
| **NAVSIM-E** | 2364-token subset used in our corruption / collision study |

`scene_filter/navsim-e.yaml` lists all tokens. `manifests/navsim-e_manifest.csv` adds `log_name` and corruption metadata.  
**Dataset makeup (2364 tokens, three pools, corruption mix):** [dataset_composition.md](dataset_composition.md).

## Evaluation with NAVSIM v2

1. Clone [autonomousvision/navsim](https://github.com/autonomousvision/navsim) (v2 / main).
2. Install dependencies and download maps + **test** data.
3. Add this repo’s `navsim-e.yaml` under  
   `navsim/planning/script/config/common/train_test_split/scene_filter/`.
4. Point `navsim_log_path` / sensor paths to your OpenScene tree (or extracted subset).
5. Run metric caching and PDM scoring with  
   `train_test_split.scene_filter=navsim-e`.

Exact shell commands depend on your agent; mirror the upstream `run_metric_caching.sh` / `run_pdm_score` scripts.

## Corruption handling

Corrupted cameras are **not** part of the official OpenScene download. They are **offline augmentations** of `sensor_blobs/test` (e.g. snow / night / spatter), stored in separate folders. This repo only ships the **token list** and the **`selected_source`** column in `manifests/navsim-e_manifest.csv`.

**Steps:**

1. Download OpenScene **`test`** (`navsim_logs` + `sensor_blobs`) and nuPlan **maps** (see [NAVSIM install](https://github.com/autonomousvision/navsim/blob/main/docs/install.md)).
2. Obtain corruption camera trees (`sensor_blobs_snow`, `sensor_blobs_spatter`, `sensor_blobs_night`, or your lab’s equivalent paths).
3. For each token, read **`selected_source`** in `navsim-e_manifest.csv` and use the matching camera root:

| `selected_source` | Camera images |
|-------------------|---------------|
| `raw` | `$OPENSCENE_DATA_ROOT/sensor_blobs/test` |
| `snow` | `.../sensor_blobs_snow/test` |
| `spatter` | `.../sensor_blobs_spatter/test` |
| `night` | `.../sensor_blobs_night/test` |

4. **LiDAR:** if a corruption folder has cameras only, keep point clouds from **`sensor_blobs/test`** (see [Lidar fallback](#lidar-fallback) below).
5. Run NAVSIM with `scene_filter/navsim-e.yaml` (`train_test_split.scene_filter=navsim-e`). Point `OPENSCENE_DATA_ROOT` (or your agent config) at the correct logs + sensor paths per token.

When building a on-disk subset with `scripts/extract_subset.py`, set `--src-sensor-blobs` to the corruption root for that batch, and use `--src-sensor-blobs-lidar` for the original `sensor_blobs` if needed.

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
