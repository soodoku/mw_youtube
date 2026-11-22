# Who appears in Delhi street-food videos?

The main dining measure counts anyone visibly eating or holding their own serving, sitting or standing with it in front of them, or sharing a meal. See the [revised Muse prompt](config/apparent_diner.json) and its [strict response schema](config/apparent_diner_response.schema.json).

Women accounted for **16.1% of the people whose apparent gender Muse could classify** in 450 randomly sampled frames from 30 Delhi street-food videos published in 2025. Among people Muse coded as taking a bite at a stall or restaurant, the estimate was **21.3%**. That second figure rests on just 15 sightings across 10 videos. The sample tells us considerably more about who appears on camera than about who eats at these establishments.

## Earlier visible-bite measure

A bite requires food or a loaded utensil reaching the mouth, or food visible in the mouth. A person holding a plate, working behind a counter, or waiting to order can appear in the overall count without entering the bite count. The broader meal measure includes drinking and people visibly eating a served meal between bites.

| People seen in the sampled frames | Women | Men | Women’s share | 95% interval |
| --- | ---: | ---: | ---: | ---: |
| All classified sightings, in any setting | 123 | 766 | 16.1% | 8.4% to 24.6% |
| Taking a bite at a stall or restaurant | 3 | 12 | 21.3% | 0.0% to 40.5% |
| Taking a bite, excluding apparent hosts and vendors | 2 | 6 | 24.5% | 0.0% to 50.7% |
| Eating a meal or drinking, including time between bites | 8 | 41 | 19.3% | 2.9% to 34.8% |

The counts are raw sightings. The percentages weight the sampled moments so each video contributes the same total time weight. A person who appears in several frames counts each time. The intervals come from resampling whole videos. The denominator includes adolescents and adults coded as women or men. Across all frames, Muse also recorded 311 adolescent or adult sightings with unclear gender, 95 with unclear age, and 22 younger children. [Frame counts](data/delhi_2025_street_food/analysis/delhi30_dining/muse/frames.csv) · [Individual sightings and visual cues](data/delhi_2025_street_food/analysis/delhi30_dining/muse/sightings.csv)

Seven of the 15 people Muse coded as taking a bite were apparent hosts. None was coded as a vendor. Of the eight remaining sightings, only two were clearly identifiable as nonhosts. The other six had uncertain presenter status. Thirteen of the 15 bite sightings came from stalls and two from restaurants. [Estimates by role, venue, and frame quality, with video and channel intervals](data/delhi_2025_street_food/analysis/delhi30_dining/muse/estimates.csv)

### What a still image can establish

In one frame a woman has a spoon at her lips above her bowl. In another, Muse reported that a man in a light blue shirt was taking a bite, but both hands appear down by his plate. Reviewing every positive label against its JPEG, Codex found clear support for seven of the 15 venue-linked bites. Those seven comprised two women and five men, a weighted share of **27.7%**, with a video interval of **0.0% to 79.6%**. Removing apparent hosts and vendors left just three visually supported sightings. This check measures how disputed positives affect the estimate. Missed eaters remain a source of uncertainty. [Spoon at the mouth, 7:16](https://www.youtube.com/watch?v=qZy8Xravrk0&t=436s) · [Crowded counter, 0:38](https://www.youtube.com/watch?v=ZmBfCcLxi2c&t=38s) · [Frame-by-frame review](data/delhi_2025_street_food/runs/delhi30_per_minute/bite_review.csv) · [Estimates after review](data/delhi_2025_street_food/analysis/delhi30_dining/muse/visually_supported_bites.csv)

## Where the frames came from

Seventy-two YouTube searches returned 1,205 distinct videos. The sampler put the uploads in a seeded random order. Reviewers worked down that list until 30 videos from 26 channels qualified. Each qualifying upload showed original footage of a public-facing food stall in Delhi. Restaurant scenes enter the sample when they appear in those uploads. The estimates describe the footage that creators filmed, edited, and published. [Selected videos and eligibility evidence](data/delhi_2025_street_food/selected_30.csv) · [Search phrases and the videos they returned](data/delhi_2025_street_food/search_hits.csv) · [Sampling plan](VIDEO_SAMPLING_PLAN.md)

The sampler divided each video into thirds and drew about one random instant per minute in each third, up to ten per third. This produced 3 to 30 frames per video. Of the 450 frames, 84 showed no enumerable person and 107 were too crowded or occluded for a complete count. The main estimates retain the people Muse could distinguish in those partial frames. Restricting the analysis to the 343 fully countable frames gives an overall share of 14.0%. [Sampled timestamps, weights, and image fingerprints](data/delhi_2025_street_food/analysis/delhi30_per_minute/muse/delhi_2025_street_food_delhi30_per_minute_muse_frames.csv) · [Study design](DESIGN.md)

## Reproduce the estimates

The published frame and sighting tables contain everything needed to recalculate the results. From the repository root, this command reads both tables, applies the saved visual review, and rebuilds the estimate files without calling an API.

```sh
PYTHONPATH=scripts python3 - <<'PY'
from pathlib import Path
from mw_youtube.records import read
from summarize_dining import write_estimates

snapshot = Path("data/delhi_2025_street_food")
out = snapshot / "analysis/delhi30_dining/muse"
review = snapshot / "runs/delhi30_per_minute/bite_review.csv"
write_estimates(read(out / "frames.csv"), read(out / "sightings.csv"), out, review)
PY
```

### Sample and code another draw

The importable package exposes `plan_searches`, `read_frames`, and `build_frames`. Install it with `python -m pip install -e .`. The search design takes a city, publication year, and topic. For example, `list(plan_searches("delhi", 2025, "street_food"))` returns the Delhi search specifications. [Discovery and analysis scripts](scripts/) · [Earlier six-frame pilot](data/delhi_2025_street_food/analysis/pilot1/muse/delhi_2025_street_food_pilot1_muse_frames.csv)

For frame collection, enable remote debugging at `chrome://inspect/#remote-debugging` in the signed-in YouTube Premium Chrome profile and allow the connection. If Chrome uses a port other than 9222, set `MW_YOUTUBE_CHROME_PORT`. The runner resumes the ranked queue and skips frames already saved. Use `--status` for progress or increase `--target` for a larger draw.

```sh
snapshot=data/delhi_2025_street_food
uv run --with-requirements requirements-frames.txt python scripts/duration_draw.py \
  "$snapshot" --target 30
```

The dining coder uses `museclient` with `muse-spark-1.3-contributor`. Each request contains one JPEG and its frozen publisher metadata. Muse returns a frame record and one row per visible person. Consumption, venue link, vendor role, and host status have separate, finite categories. The 450 calls cost **$0.286** at the recorded usage rates. [Coding dictionary](config/stall_frame_codebook_v5.json) · [Strict response schema](config/stall_frame_v5_response.schema.json) · [Spending record](data/delhi_2025_street_food/analysis/delhi30_dining/muse/spend.json)

```sh
client='museclient @ git+https://github.com/gojiplus/museclient@2063b1bb1b58a396509b2ca0f3ca52c27138a648'
uv run --no-project --with "$client" python scripts/code_dining_draw.py \
  "$snapshot" "$snapshot/selected_30.csv" --cap-usd 1
python3 scripts/summarize_dining.py \
  "$snapshot/analysis/delhi30_per_minute/muse/delhi_2025_street_food_delhi30_per_minute_muse_frames.csv" \
  "$snapshot/coding_v5" "$snapshot/analysis/delhi30_dining/muse" \
  --bite-review "$snapshot/runs/delhi30_per_minute/bite_review.csv"
```

Add `--pilot "$snapshot/runs/delhi30_per_minute/dining_pilot.json"` to the coding command to run the ten-frame pilot. The full run reuses those responses and shares its spending cap with the pilot. Local review packets preserve the JPEG fingerprints, publisher metadata, human coding sheets, and model receipts.
