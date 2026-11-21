# Who appears at street-food stalls on YouTube?

This study counts people visibly working at or using food stalls in sampled videos. The first collection covers uploads published in 2025 about Delhi. The city, topic, language and publication period determine which searches run. Each video found by those searches receives one place in the draw.

[Study design and stage contracts](DESIGN.md) · [Pilot frame data](data/delhi_2025_street_food/analysis/pilot1/muse/delhi_2025_street_food_pilot1_muse_frames.csv) · [Discovery phrases and ranks](data/delhi_2025_street_food/analysis/pilot1/muse/delhi_2025_street_food_pilot1_muse_discovery_hits.csv)

## Use from Python

Install the checkout with `python -m pip install -e .`, or run Python from its root using `uv run python`. The import interface uses the Python standard library.

```python
from pathlib import Path
from mw_youtube import plan_searches, read_frames

queries = list(plan_searches("delhi", 2025, "street_food"))
snapshot = Path("data/delhi_2025_street_food")
rows = read_frames(next((snapshot / "analysis/pilot1/muse").glob("*_frames.csv")))
print(len(queries), len(rows))  # 72 searches, 6 sampled moments
```

Each returned row has typed timing and count fields, stable video and channel IDs, and Python `None` for missing values. Pass the rows to `pandas.DataFrame.from_records` to work with a dataframe. The package also exposes `build_frames(snapshot, selection, coding_directories, coder)` for rebuilding frame rows, video coverage and search hits from frozen inputs.

## Run Delhi

With Google Chrome installed, the following command resumes the verified prefix of the ten-video draw. It saves the next unresolved rank in `runs/delhi10/status.json`. Without a spending cap it prepares images and blind worksheets and reuses completed annotations. See the design for the shared-ledger option for new Muse calls.

```sh
uv run --with-requirements requirements-frames.txt python scripts/run_draw.py \
  data/delhi_2025_street_food --draw delhi10 --target 10
```
