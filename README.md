# Who appears at street-food stalls on YouTube?

This study counts people visibly working at or using food stalls in sampled videos. The first collection covers uploads published in 2025 about Delhi. The city, topic, language and publication period determine which searches run. Each video found by those searches receives one place in the draw.

[Delhi 30-video sample](data/delhi_2025_street_food/selected_30.csv) · [450 sampled moments](data/delhi_2025_street_food/analysis/delhi30_per_minute/muse/delhi_2025_street_food_delhi30_per_minute_muse_frames.csv) · [Study design and stage contracts](DESIGN.md) · [Pilot frame data](data/delhi_2025_street_food/analysis/pilot1/muse/delhi_2025_street_food_pilot1_muse_frames.csv) · [Discovery phrases and ranks](data/delhi_2025_street_food/analysis/pilot1/muse/delhi_2025_street_food_pilot1_muse_discovery_hits.csv)

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

Open `chrome://inspect/#remote-debugging` in your signed-in YouTube Premium Chrome profile, enable remote debugging, and allow the connection when Chrome asks. If Chrome shows a port other than 9222, set `MW_YOUTUBE_CHROME_PORT` to that number. The runner opens its own watch tab, checks the Premium logo, and closes that tab after capture. The current target is 30 eligible uploads. The command reuses all completed images, checkpoints each new image, and prepares vendor and host coding packets with the publisher metadata. A larger target continues the same ranked queue. New Muse calls require `--cap-usd` and use the shared v4 ledger.

```sh
uv run --with-requirements requirements-frames.txt python scripts/duration_draw.py \
  data/delhi_2025_street_food --target 30
```

Add `--status` to the command to get a live count of verified JPEGs and completed uploads.

Each third of a video contributes one random moment per minute of its duration, rounded up and capped at ten. Thus each upload supplies 3–30 images. The images live under `frames/per_minute/VIDEO_ID/`. Each v4 review folder has the human worksheets, JSON response schema and exact video metadata supplied to Muse. A provisional manifest lists reviewed uploads while earlier ranks await adjudication. The runner freezes `selected.csv` when every preceding decision is resolved.

## Code eating and drinking

The contributor model receives one JPEG and the frozen publisher metadata for its video. Each sighting has a venue link, visible action, apparent age/gender group, service role, and presenter status. Someone selling a meal can also be eating or presenting. The [coding dictionary](config/stall_frame_codebook_v5.json) specifies the visual evidence for each label. The [response schema](config/stall_frame_v5_response.schema.json) is generated from that dictionary.

```sh
snapshot=data/delhi_2025_street_food
client='museclient @ git+https://github.com/gojiplus/museclient@2063b1bb1b58a396509b2ca0f3ca52c27138a648'
uv run --no-project --with "$client" python scripts/code_dining_draw.py \
  "$snapshot" "$snapshot/selected_30.csv" --cap-usd 1
python3 scripts/summarize_dining.py \
  "$snapshot/analysis/delhi30_per_minute/muse/delhi_2025_street_food_delhi30_per_minute_muse_frames.csv" \
  "$snapshot/coding_v5" "$snapshot/analysis/delhi30_dining/muse"
```

For the ten-frame check, add `--pilot "$snapshot/runs/delhi30_per_minute/dining_pilot.json"` to the coding command. The full run reuses the successful pilot responses. All calls share the cap and ledger. Each completed frame has a receipt. The analysis requires a receipt for every sampled frame and checks its JPEG fingerprint, model, and codebook. The exports link to the source video at the sampled instant.
