# Women’s Share of Diners at Delhi Food Stalls and Restaurants: Evidence from YouTube Videos

Women made up **13.5% of apparent diner sightings** at food venues in 30 Delhi street-food videos published in 2025. Across 450 randomly sampled frames, Muse identified 16 women and 116 men who appeared to have food of their own or to be sharing a meal. Eighteen videos contributed to that estimate. Across everyone visible whose apparent gender Muse could classify, women’s share was **16.1%**.

A pair standing at a metal table in one video illustrates who counts. The woman has a plate of pav bhaji in front of her. The man has his own serving and is talking to the camera. Both count as diners. The people at the pharmacy counter behind them also enter the overall count. In another clip, a vendor wraps food for a customer. Handling that order makes him visible as a vendor and gives no evidence that he is having a meal. [Pair at the table, 4:21](https://www.youtube.com/watch?v=oT4YH9ZtUsM&t=261s) · [Vendor wrapping food, 20:44](https://www.youtube.com/watch?v=1Ma3i47B8RY&t=1244s)

## Who counts as a diner?

Of the 132 classified diner sightings, 79 people held their own serving, 29 had food in front of them, five were sharing a dish, and 19 were visibly eating. Someone can qualify while standing, talking, or pausing between mouthfuls. The same rule applies to presenters and vendors. A personal drink without food has its own label. Including those sightings raises women’s share to **21.4%** (31 women and 128 men). [Muse prompt and coding categories](config/apparent_diner.json) · [Strict response schema](config/apparent_diner_response.schema.json)

| Sightings in the sampled footage | Women | Men | Women’s share | 95% interval |
| --- | ---: | ---: | ---: | ---: |
| Apparent diners at a food venue | 16 | 116 | 13.5% | 0.9% to 27.6% |
| Excluding apparent hosts | 10 | 71 | 14.7% | 0.9% to 34.0% |
| Excluding vendors | 16 | 113 | 14.9% | 1.0% to 30.4% |
| Excluding both | 10 | 68 | 17.2% | 1.1% to 39.9% |
| Everyone visible, in any setting | 123 | 766 | 16.1% | 8.4% to 24.6% |

The counts are raw appearances. The percentages use the sampled moments to give each video the same total time weight. This is why 16 of 132 sightings gives a weighted share of 13.5% and a raw share of 12.1%. The intervals come from resampling whole videos. Repeated appearances count each time a person is seen. The denominator includes adolescent and adult sightings coded as women or men. Among apparent diners at food venues, 14 more sightings had unclear gender and three had unclear age. [All estimates, including intervals by channel](data/delhi_2025_street_food/analysis/delhi30_apparent_diners/muse/estimates.csv)

Presenter status was unclear for 57 of the 132 classified diners. The host exclusion removes the 51 apparent hosts and retains uncertain cases. Requiring positive evidence that a diner was neither a host nor a vendor leaves 3 women and 19 men. Venue judgments also matter. Including diners whose connection to a food venue was uncertain gives 15.8%. Requiring both the person’s surroundings and the original frame label to identify a food venue gives 14.6%. [Individual sightings, timestamps, roles, and visual evidence](data/delhi_2025_street_food/analysis/delhi30_apparent_diners/muse/sightings.csv)

## Where the frames came from

Seventy-two YouTube searches returned 1,205 distinct videos. The sampler put the uploads in a seeded random order. Reviewers worked down that list until 30 videos from 26 channels qualified. Each qualifying upload showed original footage of a public-facing food stall in Delhi. Restaurant scenes enter the sample when they appear in those uploads. The estimates describe whom creators filmed and included in their published videos. [Selected videos and eligibility evidence](data/delhi_2025_street_food/selected_30.csv) · [Searches and the videos they returned](data/delhi_2025_street_food/search_hits.csv) · [Saved YouTube search and metadata responses](data/delhi_2025_street_food/responses/) · [Sampling plan](VIDEO_SAMPLING_PLAN.md)

The sampler divided each video into thirds and drew about one random instant per minute in each third, up to ten per third. This produced 3 to 30 frames per video. Of the 450 frames, 84 showed no enumerable person and 107 were too crowded or occluded for a complete count. The main estimates include everyone Muse could distinguish in those partial frames. Restricting the analysis to the 343 fully countable frames gives 8.6% women among diners and 14.0% overall. [Frame counts and image fingerprints](data/delhi_2025_street_food/analysis/delhi30_apparent_diners/muse/frames.csv) · [Study design](DESIGN.md)

## Reproduce the estimates

The published frame and sighting tables contain the data for all 34 estimates. Run this from the repository root to calculate the main result without calling an API.

```sh
PYTHONPATH=scripts python3 - <<'PY'
from pathlib import Path
from mw_youtube.records import read
from summarize_dining import estimates

out = Path("data/delhi_2025_street_food/analysis/delhi30_apparent_diners/muse")
frames, people = read(out / "frames.csv"), read(out / "sightings.csv")
main = next(estimates(frames, people, ("apparent_diner",)))
print(main["n_women"], main["n_men"], round(main["percent_women"], 1))
# 16 116 13.5
PY
```

The analysis uses the same `museclient` contributor model in both coding passes. The first pass enumerates the people in each frame and records apparent gender, venue role, and presenter status. The second pass gives Muse the original JPEG, publisher metadata, and a numbered description locating each person. Muse records the evidence of a meal and whether the person appears at a food venue. The 366 frames containing people required a second call. Their diner labels cost $0.181, bringing both passes to $0.467. The earlier bite-based measure is available as a sensitivity check. [Spending record](data/delhi_2025_street_food/analysis/delhi30_apparent_diners/muse/spend.json) · [Earlier bite-based estimates](data/delhi_2025_street_food/analysis/delhi30_dining/muse/estimates.csv)


### Sample and code another draw

The importable package exposes `plan_searches`, `read_frames`, and `build_frames`. Install it with `python -m pip install -e .`. The search design takes a city, publication year, and topic. For example, `list(plan_searches("delhi", 2025, "street_food"))` returns the Delhi search specifications. [Discovery and analysis scripts](scripts/) · [Earlier six-frame pilot](data/delhi_2025_street_food/analysis/pilot1/muse/delhi_2025_street_food_pilot1_muse_frames.csv)

For frame collection, enable remote debugging at `chrome://inspect/#remote-debugging` in the signed-in YouTube Premium Chrome profile and allow the connection. If Chrome uses a port other than 9222, set `MW_YOUTUBE_CHROME_PORT`. The runner resumes the ranked queue and skips frames already saved. Use `--status` for progress or increase `--target` for a larger draw.

```sh
snapshot=data/delhi_2025_street_food
uv run --with-requirements requirements-frames.txt python scripts/duration_draw.py \
  "$snapshot" --target 30
```

After capture, build the person roster and code the apparent diners. Both coding commands share one cumulative ledger. Each reuses its completed contributor responses.

```sh
client='museclient @ git+https://github.com/gojiplus/museclient@2063b1bb1b58a396509b2ca0f3ca52c27138a648'
uv run --no-project --with "$client" python scripts/code_dining_draw.py \
  "$snapshot" "$snapshot/selected_30.csv" --cap-usd 1
python3 scripts/summarize_dining.py \
  "$snapshot/analysis/delhi30_per_minute/muse/delhi_2025_street_food_delhi30_per_minute_muse_frames.csv" \
  "$snapshot/coding_v5" "$snapshot/analysis/delhi30_dining/muse"
roster="$snapshot/analysis/delhi30_dining/muse"
out="$snapshot/analysis/delhi30_apparent_diners/muse"
uv run --no-project --with "$client" python scripts/code_apparent_diners.py \
  "$snapshot" "$roster" --cap-usd 1
python3 scripts/summarize_apparent_diners.py "$snapshot" "$roster" "$out"
```

For the ten-frame diner pilot, add `--pilot "$snapshot/runs/delhi30_per_minute/apparent_diner_pilot.json"` to the apparent-diner coding command.
