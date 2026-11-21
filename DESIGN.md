# Study design and collection protocol

The study asks what share of classified sightings of workers and patrons at street-food stalls in sampled YouTube footage are coded as women. Delhi and Mumbai were chosen for comparisons with earlier street imagery. The first collection covers Delhi NCT, publication year 2025. Creators choose when and where to film, what to show and how long to show it. The population the draw can describe is eligible uploads retrieved by the frozen searches. Publication date defines the cohort. Filming date is a separate, usually missing field.

## Stages and handoffs

| Step | Decision and code | Record to preserve |
| --- | --- | --- |
| 1. Propose keywords | Define a topic and city. An analyst can draft multilingual phrases or use a structured Muse call in `scripts/expand_keywords.py propose`. | Draft keywords, concept, language, phrase template, prompt, model and provider call ID when applicable. |
| 2. Freeze vocabulary | Review relevance and spelling in each language. Edit the draft and use `expand_keywords.py freeze`. The first Delhi wave used the reviewed, configured vocabulary. | Reviewer, date, topic definition and versioned phrase list. A change starts a new wave. |
| 3. Build the search plan | Cross city-specific phrases with publication quarters and duration bands using `plan_searches`. | `queries.json` with exact official API parameters and stable search IDs. |
| 4. Discover and enrich uploads | `collect_candidates.py collect` calls YouTube Data API v3 search.list and videos.list. A completed snapshot replays offline. | Dated response items locally, per-query counts including zeros, every hit and its result rank, deduplicated candidates and one metadata record per upload. |
| 5. Rank and screen | `sample_videos.py queue` fixes ranks. `screen_eligibility.py` applies explicit publisher-credit rules and optional capped Muse text screening. Check qualifying footage and location in rank order. | Original rank, reviewer, date, decision, reason, place, evidence, machine ledger and timestamped `footage_reviews.csv`. |
| 6. Select | `sample_videos.py select` takes the first ten verified eligible uploads. The city runner can process the verified prefix as review proceeds. | Frozen selected IDs and seeds, next unresolved rank and any shortfall. |
| 7. Sample moments and obtain images | `acquire_frames.py` draws across the entire timeline. Chrome captures the displayed pixels. File decoding is available for supplied or downloaded footage. | Per-video `plan.json`, six JPEGs and `complete.json` with requested times, observed player times or decoded presentation times, hashes and completion status. |
| 8. Code | `prepare_frame_review.py` provides blind sheets. `code_stall_frames.py` codes each original JPEG separately. A human independently uses the same dictionary. | One frame record and zero or more person sightings per frame, coder, dictionary fingerprint, model and receipts. |
| 9. Analyze | `build_analysis_frames.py` or imported `build_frames` joins one coder to the complete draw. `summarize_stall_frames.py` reports counts by scope. | Separate frames, selected-video coverage and discovery-hit tables. Cluster keys and time weights accompany the outcome. |

## Search population and selection

The first Delhi vocabulary contains three English phrases (Delhi street food, Delhi food stall, Delhi roadside food) and three Hindi phrases (दिल्ली स्ट्रीट फूड, दिल्ली खाने का ठेला, दिल्ली सड़क किनारे खाना). Four quarters and three API duration bands give 72 searches. Request the top 25 relevance-ranked public video results per search, with the viewing region set to India. Overlap across searches gives multiple discovery routes. Deduplicate on city and video ID before ranking. Include an ID with at least one hit whose published timestamp lies in the requested window. Keep out-of-window hits for search diagnostics. Hindi relevance hints and a video's reported audio language are separate variables. [YouTube search](https://developers.google.com/youtube/data/reference/rest/v3/search/list) · [Video metadata](https://developers.google.com/youtube/data/reference/rest/v3/videos/list)

Order IDs by SHA-256 of `20261121|city|video_id`, breaking ties by ID. Include original on-location footage of food prepared or sold at a street-facing stall, cart or open-air stand inside the city boundary. Shorts and multi-stall tours qualify. Require identifiable evidence of the location. Exclude scripted episodes, reposts, home recipes, indoor-only restaurant visits and cross-city compilations. A named market and a visible service counter provide different pieces of evidence. Counts of people, camera framing and apparent gender play no part in eligibility. Keep unresolvable cases at their rank for adjudication. If a selected source becomes unavailable, record the loss and link any reserve substitution to the original selection.

The deterministic TV screen requires a named series credit, cast credit and episode number. An optional text-only Muse pass requires exact publisher quotations for proposed exclusions or inclusions. A quoted passage can still be misinterpreted. Review conflicts and audit a seeded sample of excluded uploads as well as proposed inclusions. A positive metadata label requires a separate footage decision before selection. The original pilot reviewed publisher metadata for ranks 1–26. Ranks 22 and 26 still require footage confirmation.

## Acquisition, timing and storage

The default attaches to an existing Chrome browser with Playwright and opens a dedicated watch tab in its default context. The watch page must show YouTube’s Premium masthead. The runner stops if that check fails. Each new browser frame records `browser_session=attached_premium`. At the instant of capture the player must report the selected video ID, a matching duration and no active ad. [Playwright](https://playwright.dev/python/docs/api/class-browsertype#browser-type-connect-over-cdp) The runner uses timestamped watch links, waits for the selected recording, seeks through the browser media element and saves pixels after repaint. It checks the video duration and rejects a detected advertisement or failed seek. Record requested milliseconds and observed player time separately. A player clock does not supply an exact source presentation timestamp. Check captured pixels against the watch page during validation. Access failures stay in the ledger. Google documents playback controls and metadata through its official APIs. Pixel capture uses Chrome’s rendered video element. [Player API](https://developers.google.com/youtube/iframe_api_reference)

For exact decoded times, use `--local-sources DIRECTORY` with `VIDEO_ID.mp4`, or explicitly select the third-party downloader with `--allow-yt-dlp`. Process one source at a time. In download mode, cap a rendition at 256 MiB by default and reserve 1 GiB of free space plus transfer headroom. Keep the owned spool file through a recoverable extraction failure. Release it immediately after every expected JPEG decodes and its checksum matches the completion record. Supplied originals stay with their owner. For file-based inputs save the source SHA-256, duration, time base and integer presentation timestamps. The historical first pilot used a 372 MiB 720p file under a one-video 400 MiB override. Its verified JPEGs occupy 933,066 bytes. The temporary video was released.

Divide duration into three equal-time intervals. For each interval rank integer millisecond instants by SHA-256 of `frames|seed|video_id|interval|requested_ms`, with timestamp as tie breaker. Keep the first two. Higher draw ranks extend the sample on unchanged source duration. Multiple moments may legitimately display the same image. Keep food close-ups, empty frames and cutaways. Uploads differ in editing and viewability; retaining these moments permits coverage diagnostics. Purposeful screen-review stills must stay outside the random frame draw.

## Coding, denominator and uncertainty

For each frame select exactly one value for setting, shot composition, relation to service area and countability. For each distinguishable person select a food-service role, apparent demographic category and visible activity. The [finite dictionary](config/stall_frame_codebook.json) defines every label. The linked rows have consecutive person IDs within each frame. Adult/adolescent woman or man, gender unclear, younger child and age unclear are distinct categories. Keep evidence notes separate. Host identification is deferred. Human and Muse coders see the image alone. The publisher's title and description remain available by video ID for separate contextual work.

The primary numerator is the count coded as women among stall workers and patrons. The denominator is the corresponding count coded as women or men. A readable frame with a clearly nonstall setting contributes zero to a stall count even when unrelated crowd counts are incomplete. In a countable frame with no enumerable people the count is also zero. Unknown setting with visible people, an unreadable image, incomplete counts among potential stall participants, or missing coding yields a missing primary count. Report indeterminate gender, age and countability by role. Compare workers, patrons, people of uncertain relationship, everyone in confirmed stalls, and everyone visible. People can reappear across moments.

Give each complete video total initial weight one. A moment's weight is its interval's fraction of eligible milliseconds divided by the number of draws in that interval. Estimate the city share by dividing weighted summed women sightings by weighted summed classified sightings. Report missing observations, their distribution across videos, and sensitivity to incomplete videos. A zero classified denominator gives an undefined share. Cluster uncertainty by video for repeated moments. Assess clustering by channel and sensitivity to omitting each channel for creators with repeated uploads. For a small sampling fraction the between-video variability of the ratio's linearized numerator gives a first approximation. A finite population correction requires enumerating eligible videos and accounting for within-video sampling. No design-based claim about a city's residents or visitors follows from these search results.

Pilot validation should independently code all frames, including close-ups and cutaways, before inspecting Muse labels. Report agreement on setting and counts by role and apparent gender. Compare discovery, selection and acquisition yields by query language, duration, channel and place, alongside the number of readable, empty and indeterminate moments. Source availability and coding disagreement are distinct from sampling error.

## Stage contracts and directory layout

Each collection occupies `data/CITY_YEAR_TOPIC/`; repeat searches go under `waves/WAVE/`. An analyst can supply a custom snapshot directory. Freeze the query plan, retain all discovery routes and use a new wave for new keywords. The default table export is `analysis/DRAW/CODER/CITY_YEAR_TOPIC_DRAW_CODER_frames.csv` with companion `_video_coverage.csv` and `_discovery_hits.csv`. Each video has a `frames/VIDEO_ID/` directory and one coding directory per protocol, such as `coding_v3/VIDEO_ID/`.

- [Keyword schema](config/keywords.schema.json) specifies one entry per stable keyword ID. A draft must cover each requested language and use one city placeholder per template.
- [Discovery result](config/result.schema.json) records the city, cohort, counts and paths. [Metadata rows](config/video_metadata.schema.json) retain optional fields as null and snapshot time for engagement measures. Location tags are publisher supplied.
- [Frame response schema](data/delhi_2025_street_food/coding_v3/oEEO85utSZs/muse_response.schema.json) and archived codebook travel with the frozen image manifest. Verify sampled time, source identity and JPEG hash before joining labels.
- [Analysis table contracts](config/analysis_tables.json) specify column names, types, nulls and distinct keys. Frames link to selected videos by collection/draw/video ID and carry channel ID, displayed or player timing, and within-video weights. Discovery hits have search ID and result rank. Joining the hit table directly to frame observations repeats a frame for every keyword match.

## Running individual stages

```sh
snapshot=data/delhi_2025_street_food
python scripts/collect_candidates.py plan --city delhi --year 2025 --topic street_food
python scripts/collect_candidates.py collect --city delhi --year 2025 --topic street_food
# On a new snapshot, create the ranked screening sheet once.
python scripts/sample_videos.py queue "$snapshot"
python scripts/screen_eligibility.py "$snapshot"
python scripts/sample_videos.py select "$snapshot" --target 10
```

A new search requires a YouTube Data API key in `YOUTUBE_API_KEY`. A completed snapshot can be inspected without credentials. Optional keyword expansion precedes search and requires its own authorized cap. Edit the draft before freezing it. Pass the approved artifact as `--vocabulary frozen.json` when planning and collecting a **new wave**.

```sh
python scripts/expand_keywords.py propose --city delhi --topic street_food \
  --description "Public-facing food stalls, carts and open markets" \
  --cap-usd "$KEYWORD_CAP" --ledger "$LEDGER" draft.json
python scripts/expand_keywords.py freeze draft.json frozen.json --reviewer "$REVIEWER"
```

The [README](README.md) gives the resumable city command. Run paid stages in the same environment with `museclient @ git+https://github.com/gojiplus/museclient@2063b1bb1b58a396509b2ca0f3ca52c27138a648`. Add `--cap-usd AMOUNT` to the city command only for authorized new frame coding. It uses one shared ledger per draw. Each frozen upload receives at most six requests in the initial round. Inspect the first captures, then monitor countability, invalid responses, cost and remaining disk. Preserve cached judgments when rerunning. Rebuild the original pilot export offline with:

```sh
python scripts/build_analysis_frames.py "$snapshot" "$snapshot/selected_1.csv" \
 --draw pilot1 --coder muse --coding "$snapshot/coding_v3/oEEO85utSZs"
```

## Delhi pilot and audit record

On November 21, 2026, 72 completed queries returned 1,800 hits, 1,205 unique candidate uploads and 573 channels. Hindi-only queries contributed 534 unique IDs, English-only 390 and both 281. Forty-one hits fell outside their requested quarter. All 34 affected uploads also had an in-window hit, so all 1,205 remain in the draw. The first selected upload appeared at rank 25 for “Delhi street food” and rank 6 for “दिल्ली स्ट्रीट फूड”. Of the candidates, 846 supplied audio language, 229 coordinates and 16 a recording date. [Discovery records](data/delhi_2025_street_food/result.json)

The first selected video was filmed at the open frontage of Sanjay Chur Chur Naan in Dwarka Sector 10. The April 7, 2025 date is its publication date. The six drawn moments range from 03:45.015 to 14:14.114. The first mapped to the decoded frame beginning at 225.000 seconds. Muse recorded 0 women, 2 men and 1 gender-unclear worker/patron sighting in the countable confirmed-stall frames. Six model responses cost $0.00260045 by reported token usage. These are single-video model judgments awaiting independent human validation. One video and one channel cannot support a clustered standard error. [Frame data](data/delhi_2025_street_food/analysis/pilot1/muse/delhi_2025_street_food_pilot1_muse_frames.csv)

The audit independently replayed the search-hit counts, video order and within-video hash draws. Reading the committed catalog restores nine deterministic TV exclusions that a clean checkout previously lost. Footage evidence is now required for eligibility. File-based and browser-based timing have separate fields. Record future changes to vocabulary, geography, eligibility, sampling or coding with the date, affected ranks and reason. Keep the preceding snapshot and receipts available.

On November 21, 2026 the ten-video Delhi draw reached two verified uploads and twelve sampled moments. The six Chawri Bazar frames were captured in an isolated browser before the switch to Premium. A second capture through the signed-in Premium player at 38.406, 111.955, 254.993, 329.205, 450.720 and 533.588 seconds showed matching scenes in all six pairs. The study retains the original JPEGs and hashes. Earlier frame receipts lack the new session field.
