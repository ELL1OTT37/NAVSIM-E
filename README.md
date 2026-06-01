# NAVSIM-E

**NAVSIM-E** is a curated evaluation subset for end-to-end driving on corrupted OpenScene **test** logs. It contains **2364** scene tokens with per-scene metadata (corruption type, source split, etc.).

This repository ships **definitions and tooling only**. Sensor data must be obtained under the [nuPlan / OpenScene license](https://motional-nuplan.s3-ap-northeast-1.amazonaws.com/LICENSE) via the official [NAVSIM devkit](https://github.com/autonomousvision/navsim).

## Dataset composition

| Item | Value |
|------|--------|
| Parent split | OpenScene / NAVSIM **`test`** (navtest-scale logs) |
| \# scenes | **2364** tokens (one 14-frame window per token) |
| Window | 4 history + 10 future frames, `frame_interval=1`, `has_route=true` (see `scene_filter/navsim-e.yaml`) |

**How the 2364 scenes were built** — three equal splits merged (`source_dataset` in `manifests/navsim-e_manifest.csv`):

| `source_dataset` | Count | Role (short) |
|------------------|------:|----------------|
| `extreme_merged` | 788 | Challenging / collision-related scenarios (merged extreme subset) |
| `processed_random` | 788 | Random sample with processed corruptions |
| `raw_random` | 788 | Random sample using raw (uncorrupted) cameras |

Per-token `log_name`, corruption type (`selected_source`), PDM/collision fields, and split tags are in **`manifests/navsim-e_manifest.csv`**. More detail: [docs/dataset_composition.md](docs/dataset_composition.md).

## Contents

| Path | Description |
|------|-------------|
| `scene_filter/navsim-e.yaml` | Hydra `SceneFilter` (4 history + 10 future frames) |
| `manifests/navsim-e_manifest.csv` | `token`, `log_name`, corruption / source metadata |
| `manifests/navsim-e_tokens.txt` | Token list only |
| `scripts/extract_subset.py` | Build a local mini-log + sensor subset from full OpenScene `test` |

## Quick start

### 1. Install NAVSIM

Follow [navsim/docs/install.md](https://github.com/autonomousvision/navsim/blob/main/docs/install.md):

- Download **nuPlan maps**
- Download OpenScene **`test`** (`navsim_logs` + `sensor_blobs`)

Set environment variables (example):

```bash
export NUPLAN_MAP_VERSION="nuplan-maps-v1.0"
export NUPLAN_MAPS_ROOT="$HOME/navsim_workspace/dataset/maps"
export OPENSCENE_DATA_ROOT="$HOME/navsim_workspace/dataset"
export NAVSIM_DEVKIT_ROOT="$HOME/navsim_workspace/navsim"
export NAVSIM_EXP_ROOT="$HOME/navsim_workspace/exp"
```

### 2. Use the scene filter in NAVSIM (no physical copy)

Copy or symlink `scene_filter/navsim-e.yaml` into your NAVSIM tree:

`navsim/planning/script/config/common/train_test_split/scene_filter/navsim-e.yaml`

Run training / evaluation with:

```bash
train_test_split.scene_filter=navsim-e
```

Paths should point to the official `test` logs and blobs under `OPENSCENE_DATA_ROOT`.

### 3. Optional: build a standalone subset on disk

```bash
pip install tqdm
python scripts/extract_subset.py \
  --src-navsim-logs "$OPENSCENE_DATA_ROOT/navsim_logs" \
  --src-sensor-blobs "$OPENSCENE_DATA_ROOT/sensor_blobs" \
  --dst-root "$HOME/navsim_workspace/dataset/navsim-e" \
  --split test \
  --dry-run   # remove for real copy
```

Output layout:

```text
{dst-root}/
  navsim_logs/test/{token}.pkl
  sensor_blobs/test/...
  manifest/
```

### 4. Corruption (snow / night / spatter / raw)

This repo does **not** include corrupted images. Use `manifests/navsim-e_manifest.csv` column **`selected_source`** to pick the camera folder (`sensor_blobs` for `raw`, or `sensor_blobs_snow` / `_spatter` / `_night` for corruptions). LiDAR usually stays on the original `sensor_blobs/test`.

See **[docs/setup.md](docs/setup.md#corruption-handling)** for the short step-by-step guide.

## Citation

Please cite NAVSIM and your NAVSIM-E paper when using this benchmark. (BibTeX to be added.)

## License

Code in this repository: TBD (MIT/Apache-2.0).  
Dataset usage is subject to the OpenScene / nuPlan terms.
