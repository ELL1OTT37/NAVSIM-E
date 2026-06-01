#!/usr/bin/env python3
"""
Build a NavSim subset containing only collision scenarios (by token).

Each scenario becomes one mini-log pickle with exactly ``num_history + num_future`` frames,
saved as ``navsim_logs/{split}/{token}.pkl``. Only sensor files referenced by those frames
are copied (paths inside frame dicts are preserved).

Usage with SceneLoader / caching::

    scene_filter=navtest_collision_subset
    # or: scene_filter.log_names=<list of token pkls>  # see generated tokens.txt

The generated scene filter YAML lists all token names as ``log_names`` so existing
``filter_scenes`` loads one window per ``{token}.pkl`` without extra code changes.
"""

from __future__ import annotations

import argparse
import csv
import os
import pickle
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None  # type: ignore


def _split_list(input_list: List[Any], num_frames: int, frame_interval: int) -> List[List[Any]]:
    return [input_list[i : i + num_frames] for i in range(0, len(input_list), frame_interval)]


def _find_scene_window(
    frames: List[Dict[str, Any]],
    target_token: str,
    num_history_frames: int,
    num_future_frames: int,
    frame_interval: int,
    has_route: bool,
) -> Optional[List[Dict[str, Any]]]:
    num_frames = num_history_frames + num_future_frames
    for frame_list in _split_list(frames, num_frames, frame_interval):
        if len(frame_list) < num_frames:
            continue
        if has_route and len(frame_list[num_history_frames - 1].get("roadblock_ids", [])) == 0:
            continue
        if frame_list[num_history_frames - 1].get("token") == target_token:
            return frame_list
    return None


def _sensor_paths_in_window(frame_list: List[Dict[str, Any]]) -> Set[str]:
    paths: Set[str] = set()
    for frame in frame_list:
        lidar = frame.get("lidar_path")
        if lidar:
            paths.add(str(lidar))
        for cam_dict in frame.get("cams", {}).values():
            if isinstance(cam_dict, dict) and cam_dict.get("data_path"):
                paths.add(str(cam_dict["data_path"]))
    return paths


def _is_lidar_path(rel: str) -> bool:
    return rel.endswith(".pcd") or "MergedPointCloud" in rel.replace("\\", "/")


def _resolve_sensor_src(rel: str, src_blobs: Path, lidar_src_blobs: Optional[Path]) -> Path:
    """Primary blob root; optional second root for lidar when night/camera-only trees lack .pcd."""
    primary = src_blobs / rel
    if primary.is_file():
        return primary
    if lidar_src_blobs is not None and _is_lidar_path(rel):
        fallback = lidar_src_blobs / rel
        if fallback.is_file():
            return fallback
    return primary


def _collect_paths_from_dst_pkls(dst_logs: Path) -> Set[str]:
    paths: Set[str] = set()
    for pkl_path in sorted(dst_logs.glob("*.pkl")):
        with pkl_path.open("rb") as f:
            frames = pickle.load(f)
        paths |= _sensor_paths_in_window(frames)
    return paths


def _read_collision_csv(csv_path: Path) -> List[Tuple[str, str]]:
    rows: List[Tuple[str, str]] = []
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or "token" not in reader.fieldnames:
            raise ValueError(f"CSV must contain 'token' column: {csv_path}")
        for row in reader:
            token = (row.get("token") or "").strip()
            log_name = (row.get("log_name") or "").strip()
            if token:
                rows.append((token, log_name))
    if not rows:
        raise ValueError(f"No tokens in {csv_path}")
    return rows


def _copy_sensor_paths(
    paths: Set[str],
    src_blobs: Path,
    dst_blobs: Path,
    dry_run: bool,
    file_bar: Optional[Any],
    lidar_src_blobs: Optional[Path] = None,
) -> Tuple[int, int, List[str], Dict[str, int]]:
    n_files = 0
    n_bytes = 0
    missing: List[str] = []
    stats = {"lidar_ref": 0, "lidar_copied": 0, "camera_ref": 0, "camera_copied": 0}
    for rel in sorted(paths):
        is_lidar = _is_lidar_path(rel)
        if is_lidar:
            stats["lidar_ref"] += 1
        else:
            stats["camera_ref"] += 1
        src = _resolve_sensor_src(rel, src_blobs, lidar_src_blobs)
        dst = dst_blobs / rel
        if not src.is_file():
            if dst.is_file():
                if is_lidar:
                    stats["lidar_copied"] += 1
                else:
                    stats["camera_copied"] += 1
                if file_bar is not None:
                    file_bar.update(1)
                continue
            missing.append(rel)
            if file_bar is not None:
                file_bar.update(1)
            continue
        if dst.exists() and dst.stat().st_size == src.stat().st_size:
            if is_lidar:
                stats["lidar_copied"] += 1
            else:
                stats["camera_copied"] += 1
            if file_bar is not None:
                file_bar.update(1)
            continue
        if not dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        n_files += 1
        n_bytes += src.stat().st_size
        if is_lidar:
            stats["lidar_copied"] += 1
        else:
            stats["camera_copied"] += 1
        if file_bar is not None:
            file_bar.update(1)
    return n_files, n_bytes, missing, stats


def _write_scene_filter_yaml(tokens: List[str], out_path: Path) -> None:
    lines = [
        "_target_: navsim.common.dataclasses.SceneFilter",
        "_convert_: 'all'",
        "",
        "num_history_frames: 4",
        "num_future_frames: 10",
        "frame_interval: 1",
        "has_route: true",
        "max_scenes: null",
        "log_names:",
    ]
    for tok in tokens:
        lines.append(f"  - '{tok}'")
    lines.append("tokens: null")
    lines.append("")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")


def _format_bytes(num: int) -> str:
    for unit in ("B", "KiB", "MiB", "GiB"):
        if num < 1024 or unit == "GiB":
            return f"{num:.2f} {unit}" if unit != "B" else f"{num} B"
        num /= 1024
    return f"{num:.2f} GiB"


def main(argv: Optional[List[str]] = None) -> int:
    repo_root = Path(__file__).resolve().parents[1]
    default_csv = repo_root / "manifests/navsim-e_manifest.csv"

    parser = argparse.ArgumentParser(description="Extract NavSim subset for collision scenario tokens.")
    parser.add_argument("--collision-csv", type=Path, default=default_csv)
    parser.add_argument(
        "--src-navsim-logs",
        type=Path,
        default=None,
        help="OpenScene navsim_logs root (parent of split dir). Required unless --sensors-only.",
    )
    parser.add_argument(
        "--src-sensor-blobs",
        type=Path,
        default=None,
        help="OpenScene sensor_blobs root (parent of split dir). Required unless --sensors-only.",
    )
    parser.add_argument(
        "--src-sensor-blobs-lidar",
        type=Path,
        default=None,
        help=(
            "Fallback sensor_blobs root (parent of split dir) for lidar (.pcd) when --src-sensor-blobs "
            "lacks MergedPointCloud (e.g. camera-only sensor_blobs_night)."
        ),
    )
    parser.add_argument(
        "--lidar-source-split",
        type=str,
        default=None,
        help=(
            "Split folder under --src-sensor-blobs-lidar (default: test when --split=collision_night, "
            "else same as --split)."
        ),
    )
    parser.add_argument(
        "--sensors-only",
        action="store_true",
        help="Only copy sensors into an existing subset (read {dst}/navsim_logs/{split}/*.pkl).",
    )
    parser.add_argument(
        "--require-lidar",
        action="store_true",
        default=True,
        help="Exit with code 2 if any lidar path was referenced but zero lidar files were copied.",
    )
    parser.add_argument(
        "--no-require-lidar",
        action="store_false",
        dest="require_lidar",
        help="Allow subsets without lidar (not suitable for SeerDrive / lidar agents).",
    )
    parser.add_argument(
        "--dst-root",
        type=Path,
        required=False,
        default=repo_root / "data/navsim-e",
        help="Output subset root (navsim_logs/ + sensor_blobs/ under here).",
    )
    parser.add_argument("--split", type=str, default="test")
    parser.add_argument("--num-history-frames", type=int, default=4)
    parser.add_argument("--num-future-frames", type=int, default=10)
    parser.add_argument("--frame-interval", type=int, default=1)
    parser.add_argument("--no-route-filter", action="store_true", help="Do not skip windows without route.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-existing", action="store_true")
    args = parser.parse_args(argv)

    if args.src_navsim_logs is None:
        args.src_navsim_logs = Path(
            os.environ.get("OPENSCENE_DATA_ROOT", repo_root / "data/openscene")
        ) / "navsim_logs"
    if args.src_sensor_blobs is None:
        args.src_sensor_blobs = Path(
            os.environ.get("OPENSCENE_DATA_ROOT", repo_root / "data/openscene")
        ) / "sensor_blobs"

    if tqdm is None:
        print("ERROR: tqdm required (pip install tqdm)", file=sys.stderr)
        return 1

    if args.sensors_only:
        ordered: List[Tuple[str, str]] = []
    else:
        scenarios = _read_collision_csv(args.collision_csv)
        # preserve order, unique tokens
        seen: Set[str] = set()
        ordered = []
        for token, log_name in scenarios:
            if token not in seen:
                seen.add(token)
                ordered.append((token, log_name))

    src_logs = args.src_navsim_logs / args.split
    src_blobs = args.src_sensor_blobs / args.split
    dst_logs = args.dst_root / "navsim_logs" / args.split
    dst_blobs = args.dst_root / "sensor_blobs" / args.split
    has_route = not args.no_route_filter

    lidar_split = args.lidar_source_split
    if lidar_split is None:
        lidar_split = "test" if args.split == "collision_night" else args.split

    lidar_src_blobs: Optional[Path] = args.src_sensor_blobs_lidar
    if lidar_src_blobs is not None:
        lidar_src_blobs = lidar_src_blobs / lidar_split
    else:
        default_lidar_root = Path(
            os.environ.get("OPENSCENE_DATA_ROOT", repo_root / "data/openscene")
        ) / "sensor_blobs" / lidar_split
        if default_lidar_root.is_dir() and default_lidar_root.resolve() != src_blobs.resolve():
            lidar_src_blobs = default_lidar_root

    if not args.dry_run:
        dst_blobs.mkdir(parents=True, exist_ok=True)
        if not args.sensors_only:
            dst_logs.mkdir(parents=True, exist_ok=True)

    if args.sensors_only:
        print("mode:            sensors-only (existing pkls)")
    else:
        print(f"collision csv:   {args.collision_csv} ({len(ordered)} unique tokens)")
    print(f"src logs:        {src_logs}")
    print(f"src blobs:       {src_blobs}")
    if lidar_src_blobs is not None:
        print(f"src lidar fallback: {lidar_src_blobs}")
    print(f"dst:             {args.dst_root}")
    if args.dry_run:
        print("mode:            DRY RUN")
    print()

    log_cache: Dict[str, List[Dict[str, Any]]] = {}
    missing_window: List[str] = []
    missing_log: List[str] = []
    skipped = 0
    written_pkls = 0
    total_sensor_files = 0
    total_sensor_bytes = 0
    all_sensor_paths: Set[str] = set()

    if args.sensors_only:
        if not dst_logs.is_dir():
            print(f"ERROR: --sensors-only but no pkls under {dst_logs}", file=sys.stderr)
            return 1
        all_sensor_paths = _collect_paths_from_dst_pkls(dst_logs)
        written_pkls = sum(1 for _ in dst_logs.glob("*.pkl"))
        print(f"Collected {len(all_sensor_paths)} sensor paths from {written_pkls} existing pkls")
    else:
        token_bar = tqdm(ordered, desc="Scenarios", unit="token", dynamic_ncols=True)

        for token, log_name in token_bar:
            token_bar.set_postfix_str(token[:12])

            dst_pkl = dst_logs / f"{token}.pkl"
            if args.skip_existing and dst_pkl.is_file():
                skipped += 1
                continue

            src_pkl = src_logs / f"{log_name}.pkl"
            if not src_pkl.is_file():
                missing_log.append(f"{token}:{log_name}")
                continue

            if log_name not in log_cache:
                with src_pkl.open("rb") as f:
                    log_cache[log_name] = pickle.load(f)

            window = _find_scene_window(
                log_cache[log_name],
                token,
                args.num_history_frames,
                args.num_future_frames,
                args.frame_interval,
                has_route,
            )
            if window is None:
                missing_window.append(token)
                continue

            sensor_paths = _sensor_paths_in_window(window)
            all_sensor_paths |= sensor_paths

            if not args.dry_run:
                with dst_pkl.open("wb") as f:
                    pickle.dump(window, f, protocol=pickle.HIGHEST_PROTOCOL)
            written_pkls += 1

        token_bar.close()

    n_sensor_refs = len(all_sensor_paths)
    n_lidar_refs = sum(1 for p in all_sensor_paths if _is_lidar_path(p))
    print(
        f"\nCopying {n_sensor_refs} unique sensor paths "
        f"({n_lidar_refs} lidar .pcd, {n_sensor_refs - n_lidar_refs} camera); "
        f"primary src={src_blobs}"
    )
    if lidar_src_blobs is not None:
        print(f"  lidar fallback src={lidar_src_blobs}")
    file_bar = tqdm(total=n_sensor_refs, desc="Sensor files", unit="path", dynamic_ncols=True)
    n_new, n_bytes, missing_sensor, copy_stats = _copy_sensor_paths(
        all_sensor_paths,
        src_blobs,
        dst_blobs,
        args.dry_run,
        file_bar,
        lidar_src_blobs=lidar_src_blobs,
    )
    file_bar.close()
    total_sensor_files = n_new
    total_sensor_bytes = n_bytes
    if missing_sensor:
        print(
            f"\nSensor progress: {n_sensor_refs - len(missing_sensor)}/{n_sensor_refs} paths found on disk; "
            f"{len(missing_sensor)} referenced in scene pkls but absent under {src_blobs}."
        )
        for rel in missing_sensor[:5]:
            tqdm.write(f"[MISSING] sensor: {src_blobs / rel}")
        if len(missing_sensor) > 5:
            tqdm.write(f"[MISSING] ... and {len(missing_sensor) - 5} more (see summary / manifest)")

    tokens_out = [t for t, _ in ordered]
    manifest_dir = args.dst_root / "manifest"
    if not args.dry_run:
        manifest_dir.mkdir(parents=True, exist_ok=True)
        if not args.sensors_only:
            (manifest_dir / "collision_tokens.txt").write_text(
                "\n".join(tokens_out) + "\n", encoding="utf-8"
            )
            _write_scene_filter_yaml(
                tokens_out,
                manifest_dir / "navsim-e_extracted_scene_filter.yaml",
            )
            readme = manifest_dir / "README.txt"
            readme.write_text(
                "\n".join(
                    [
                        "Collision scenario subset (one pkl per token, 14 frames each).",
                        f"Tokens: {len(tokens_out)}",
                        "",
                        "Hydra:",
                        "  scene_filter=navtest_collision_subset",
                        f"  navsim_log_path={args.dst_root / 'navsim_logs' / args.split}",
                        f"  sensor_blobs_path={args.dst_root / 'sensor_blobs' / args.split}",
                        "",
                        "Each navsim_logs file is named {token}.pkl (not log_name).",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
        if missing_sensor:
            (manifest_dir / "missing_sensor_paths.txt").write_text(
                "\n".join(missing_sensor) + "\n", encoding="utf-8"
            )

    print("\n========== Summary ==========")
    print(f"  unique tokens:      {len(ordered)}")
    print(f"  pkls written:       {written_pkls}")
    print(f"  skipped existing:   {skipped}")
    print(f"  missing log pkl:    {len(missing_log)}")
    print(f"  missing window:     {len(missing_window)}")
    print(f"  sensor paths ref:   {n_sensor_refs}")
    print(f"  lidar paths ref:    {copy_stats['lidar_ref']}")
    print(f"  lidar on disk:      {copy_stats['lidar_copied']}")
    print(f"  camera paths ref:   {copy_stats['camera_ref']}")
    print(f"  camera on disk:     {copy_stats['camera_copied']}")
    print(f"  sensor missing:     {len(missing_sensor)}")
    missing_lidar = [p for p in missing_sensor if _is_lidar_path(p)]
    if missing_lidar:
        print(f"  lidar missing:      {len(missing_lidar)}")
    print(f"  sensor files new:   {total_sensor_files}")
    print(f"  sensor bytes new:   {_format_bytes(total_sensor_bytes)}")
    print(f"  dst root:           {args.dst_root}")
    if not args.dry_run and not args.sensors_only:
        print("  scene_filter:       navsim/.../scene_filter/navtest_collision_subset.yaml")
    if not args.dry_run and missing_sensor:
        print(f"  missing sensor list: {manifest_dir / 'missing_sensor_paths.txt'}")
    if missing_log or missing_window:
        if missing_log[:3]:
            print(f"  e.g. missing log:   {missing_log[:3]}")
        if missing_window[:5]:
            print(f"  e.g. missing win:   {missing_window[:5]}")
        return 2
    if args.require_lidar and copy_stats["lidar_ref"] > 0 and copy_stats["lidar_copied"] == 0:
        print(
            "\nERROR: referenced lidar files but copied none. "
            "Use full sensor_blobs for cameras+lidar, or set --src-sensor-blobs-lidar to dataset/sensor_blobs.",
            file=sys.stderr,
        )
        return 2
    if missing_sensor:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
