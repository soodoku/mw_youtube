# Study design and collection protocol for YouTube street-food videos

Pilot design, November 2026. The first run is Delhi, publication year 2025. The deliverable is a list of 10 verified YouTube videos per city, with a dated search record and a reproducible order for selecting more. Delhi and Mumbai have existing bike-camera and Street View studies. The pilot tests whether YouTube yields footage of food stalls in those same cities. Its unit is a video upload. A vendor, a stall, or a street can appear in several uploads.

The proposed primary question is what share of classified sightings of people visibly working at or using a street-food stall are coded as women in the sampled footage. Workers and patrons can also be described separately. Creators choose the stalls, camera angles and times of day. YouTube then decides which uploads these searches retrieve. The study can describe what appears on camera among the eligible uploads in a frozen search. A claim about people visiting all stalls in Delhi would require a sampling frame for stalls and observation times.

### Delhi pilot record, November 21, 2026

| Step | What has happened | Evidence |
| --- | --- | --- |
| Discover uploads | All 72 searches returned 25 hits. The 1,800 hits contained 1,205 distinct uploads from 573 channels. Hindi queries alone found 534 uploads, English queries alone found 390, and both found 281. | [Discovery counts](data/delhi_2025_street_food/result.json) and [yield by search term and language](data/delhi_2025_street_food/discovery_yield.csv) |
| Order and screen | The first 26 ranks received a publisher-metadata review. Two received an eligible label, ten were excluded, and fourteen require more evidence. The scripted-TV rule flagged nine uploads across all ranks, including two already excluded by the reviewer. The combined ledger contains 17 exclusions. The rank 1 footage decision below supersedes one of the fourteen metadata uncertainties. The optional Muse pass has yet to run. | [Reviewer decisions](data/delhi_2025_street_food/screening.csv), [machine decisions](data/delhi_2025_street_food/machine_screening.csv) and [combined decisions](data/delhi_2025_street_food/resolved_screening.csv) |
| Select videos | The one-video pilot selected rank 1, Sanjay Chur Chur Naan in Dwarka Sector 10. The cook works at the open frontage at 00:20 and the presenter eats beside the counter at 01:00. The ten-video draw remains open. | [One-video draw](data/delhi_2025_street_food/selected_1.csv), [screening revision](data/delhi_2025_street_food/one_video_pilot/eligibility_review.json), [footage at 00:20](https://www.youtube.com/watch?v=oEEO85utSZs&t=20s) |
| Acquire and extract | The runner extracts six seeded moments from each verified upload. See the dated one-video run below for the source rendition, disk settings and output. | [Runner](scripts/acquire_frames.py) and [frame draw](scripts/sample_frames.py) |
| Code and estimate | Six JPEGs and blind review forms are ready. The current dictionary records observable settings and activities. See the one-video run below for coding status. | [Coding dictionary](config/stall_frame_codebook.json) and [pilot gallery](data/delhi_2025_street_food/coding_v3/oEEO85utSZs/human_review.html) |

## 1. Define the videos we want

Include public videos published in the requested calendar year that contain on-location footage of food being prepared or sold at a street-facing stall, cart, or open-air market stand in the target city. Include Shorts, long videos, quiet stalls, and close-ups of food. An empty stall or a shot with nobody recognizable can qualify if the setting and activity are clear. The publication date fixes the search window. Record the filming date separately when the creator supplies one.

Use Delhi NCT for Delhi and Greater Mumbai for Mumbai. A video filmed in Gurugram or Navi Mumbai belongs outside these boundaries even when the title says “Delhi NCR” or “Mumbai.” Require a named stall, market, address, or locality that places the footage inside the boundary. Record the evidence and a timestamp or description excerpt. For example, a video titled “Delhi-style chaat” filmed in London fails the location check. A food tour covering several stalls in one city qualifies. Exclude cross-city compilations, home recipes, indoor restaurant-only visits, slideshows, and identifiable reposts of someone else’s footage. Mark unresolved location or setting as unclear and seek a second decision.

## 2. Build and freeze the candidate list

For this pilot, sample directly from search results. Finding a popular channel and collecting all its uploads would give its catalog a separate route into the sample. Keeping one discovery rule makes it possible to say exactly how each candidate got in.

Select one city, publication year and topic per run. [Cities](config/cities.json) supplies the boundary, country of availability and city spelling by language. [Topics](config/topics.json) supplies a substantive description and a reviewed set of language-specific phrase templates grouped by concept. The initial vocabulary is an analyst proposal. The same concept can use idiomatic wording in each language. Add a topic or language by editing the configuration before collection and saving a new snapshot; do not regenerate translations on every run.

For Delhi, the topic is street food at public stalls, carts, and open-air market stands. The literal queries include `Delhi street food`, `Delhi food stall`, `Delhi roadside food`, `दिल्ली स्ट्रीट फूड`, `दिल्ली खाने का ठेला`, and `दिल्ली सड़क किनारे खाना`. Within each publication quarter, run each phrase in all three YouTube duration bands (under 4 minutes, 4 to 20 minutes inclusive, and over 20 minutes). Use the phrase language as a relevance hint; keep the returned default audio language separate. Request one page of up to 25 results ordered by relevance per combination. Six phrases across four quarters and three bands gives 72 search calls and at most 1,800 hits. Date windows use UTC and the time refers to publication. The country parameter sets the viewing region. Verify the actual city during screening. Search records overlapping across phrases, languages or bands count only once in the video draw. [YouTube search documentation](https://developers.google.com/youtube/data/reference/rest/v3/search/list)

Save the query, dates, parameters, request time, rank, and video ID for every result. Distinguish a completed search with zero hits from a failed request. Retry failed requests and freeze the list once all planned searches are accounted for. Save every query match, but give each video ID one place in a city's candidate list. Enrich the IDs with channel ID, title, publication timestamp, duration, and availability. Preserve the dated candidate list used for the draw because a future search can return different results. [Video metadata documentation](https://developers.google.com/youtube/data/reference/rest/v3/videos/list)

## 3. Draw and collect the videos

1. Within each city, sort the unique candidate IDs by the SHA-256 digest of the UTF-8 string `20261121|city|video_id`, substituting the lowercase city (`delhi` or `mumbai`) and the exact video ID. Sort by video ID to break a tie. Record the rank before opening any videos for screening.
2. Open videos in rank order. For each, save the eligibility decision, reason, location evidence, reviewer, and review date. Resolve unclear cases in the screened prefix before closing the draw. Select the first 10 eligible, playable videos per city. If the list runs out, report the shortfall. Screeners should decide from place and activity alone. The number or apparent gender of people visible plays no part.
3. Save the canonical watch link, video and channel IDs, publication date, duration, verified place, and a timestamp showing the qualifying setting. That timestamp documents eligibility; choosing moments for analysis is a later decision. The pilot collects a watchable video manifest. Record any separately obtained source file and its provenance if one becomes available.
4. If a selected video later disappears, keep its row and record when access failed. Take the next eligible video in the frozen order as its replacement and link the two rows. To expand to 100 per city, continue from the same ranks. Never rerun the search and silently fold new hits into the original draw.

### Eligibility screening between the draw and selection

The random ordering is frozen first. Screen for membership in the topic and city using publisher metadata. The screen never receives counts of people, demographic labels, previous decisions, view counts, or a position in the draw. Record every exclusion at its original rank.

1. Run `python3 scripts/screen_eligibility.py data/delhi_2025_street_food`. This local pass screens the full list. For the street-food pilot a show-name line naming a known scripted series, a cast credit, and an episode-number credit together identify a television episode. The initial series list came from inspecting the Delhi pilot; performance on those examples is descriptive. A food documentary can also have episodes. A mention of a show, “full episode” in a title, or a channel name alone does not trigger the rule.
2. Run a separate **text-only Muse pass on the ranked prefix**. Supply a rank limit and an authorized spending cap. Muse receives the target boundary and subject, video ID, title, and description. The protocol specifies three answers: eligible, excluded, unclear. Exclusion requires a passage directly establishing an incompatible place or activity. Eligibility requires evidence for both a specific place and a qualifying setting. The script checks that the cited text occurs verbatim in the source. A real quote can still be misinterpreted. Check both false exclusions and false inclusions against independently viewed footage before using the model at scale.
3. Review uncertain places, storefronts, and conflicting evidence in the footage. Confirm model-proposed inclusions before acquisition. Keep the decision and timestamp or description evidence in `screening.csv`. Existing reviewer decisions take priority, including an explicit request for more evidence. Quoted model exclusions can resolve previously unreviewed rows; a reviewer can reverse them. The pilot comparison should reuse the same ranks, withhold existing labels from the model, and report disagreements by reason. The previous Codex judgments are a metadata comparison, not independent footage verification. Audit exclusions on a seeded random sample as well as adjudicating disagreements; a screen can look accurate if only retained videos are checked.
4. The selector writes `resolved_screening.csv` by combining the reviewer sheet with local rules and cached decisions. It still stops at the first unresolved rank. An exclusion keeps the next rank eligible to be considered. An ambiguous upload remains in the queue. For a topic without a configured eligibility protocol, use explicit manual screening and `select --manual-only`.

The [screening protocol](config/eligibility.json) fixes the prompt, model and scripted-series vocabulary. Model receipts in `eligibility/` record the exact input, input and protocol fingerprints, checked answer, provider call reference, and review date. Museclient retains the original request, response and cost ledger. Replaying those receipts makes selection reproducible. A fresh model call can give a different answer. A changed input or protocol uses a new receipt. The same Muse ledger enforces the total run cap across restarts. Run the following command with the rank and budget approved for the current pilot:

```sh
uv run --with 'museclient @ git+https://github.com/gojiplus/museclient@2063b1bb1b58a396509b2ca0f3ca52c27138a648' python scripts/screen_eligibility.py data/delhi_2025_street_food --through-rank "$PILOT_RANK" --cap-usd "$PILOT_USD"
```

## 4. Show what the search bought us

Keep three tables: `search_hits` (one row per returned hit), `screening` (one row per city and candidate ID, including the unreviewed reserve), and `selected_videos` (one row per selected upload, with any replacement history). The first report should show, by city, raw hits, distinct IDs, candidates screened, exclusions by reason, unresolved cases, videos selected, unique channels and named locations, and the largest channel's contribution. Show three actual decisions beside the watch links and location evidence: an inclusion, an exclusion, and a borderline case if one occurs.

Every selected ID must trace to a search hit and an eligible screening record. Every earlier rank must have a disposition. The search favors what YouTube retrieves for these words. A random draw from this list can describe the eligible uploads it contains. It does not establish how common a street scene is across a city. View counts, channel concentration, and repeated visits to the same market are useful descriptions of what the collection covers.

## Pipeline and reproducibility

| Stage | Unit and decision | Record passed to the next stage |
| --- | --- | --- |
| 1. Find and draw videos | Draw an upload from the verified, publicly playable candidates returned by the frozen city searches. Use the ranked screening queue above. | Search plan and hits, candidate metadata, screening decisions, selected video IDs and ranks. |
| 2. Obtain the selected videos | Attempt access to every selected upload. A watch link suffices for manual review. Where a source file is available for analysis, record how it was obtained. | One acquisition record per attempt with video ID, access date, status, duration, and, for a local file, path, checksum and time base. Keep losses in the original sample. |
| 3. Sample moments within each video | For the pilot, divide the whole timeline into three equal-duration intervals and draw two distinct moments per interval. Keep food close-ups and empty frames. | One row per moment with the video ID, source version, interval, random rank, requested time, decoded presentation time, and extraction status. |
| 4. Code and estimate | Human or model coding reads the same frozen frame list. Keep coder or model and prompt versions, counts, unclear cases, and review status. | Counts by frame with the IDs needed to reconstruct estimates by video, channel, and city. |

Discovery, eligibility screening, selection and serial frame extraction have command-line entry points. The original screenshot notebook is exploratory. Any later reserve substitution requires a separate record linking it to the original selection and the reason for loss. The acquisition runner stops on failure and leaves that decision to the study team.

**Within-video seed.** Fix one study seed. For each video, rank a grid of millisecond timestamps in each interval by SHA-256 of `frames|study_seed|video_id|interval|timestamp_ms` (decimal integers; zero-based intervals; break ties by time). Take the first two ranks. Additional draws take the next ranks in the same intervals. Draw from the actual source duration and save that duration and the file checksum. If a video is edited, treat it as a new source version. Map each sampled time to the frame displayed at that instant using its presentation timestamp; multiple times can legitimately show the same frame. Re-running on unchanged files, adding other videos or drawing more moments preserves earlier selections. For stage 1, `queries.json` and the saved hits fix the candidate population; the video seed alone cannot reproduce yesterday's search rankings.

**What uncertainty means here.** A natural first statistic for each city is the ratio of two sums across sampled videos: the average count coded as women among visible stall workers and patrons at a random moment in each video, summed across videos, divided by the corresponding sum coded as women or men in those roles. A readable frame clearly showing another setting contributes zero to both stall counts. Retain videos with no qualifying sightings. Report missing observations separately and state how they were handled. Give each video equal initial weight and each interval its share of the video's duration. This counts sightings and gives crowded scenes more weight in the final share. Save video, city, channel, market, interval sizes, selected times and all count denominators. Keep a zero-person frame as an observed zero and an unreadable frame as missing.

Estimate uncertainty at the level where videos were drawn, separately by city. For the proposed equal-probability video draw and small sampling fraction, a first approximation uses the between-video variation in the numerator minus the estimated share times the denominator, divided by the mean video denominator and the square root of the number of videos. The between-video variation in estimated counts already includes frame-sampling noise. If a substantial share of eligible videos was sampled, enumerate the eligible population before applying a finite-population correction and retain the within-video component. Ten videos per city support a pilot; show the individual video estimates, channel concentration, and how much the answer changes on omitting each channel. These standard errors concern repeated draws from the frozen list. Geographic and language coverage of the searches, unavailable videos, and misclassification need separate diagnostics.

### Run stage 1

From the repo root, inspect the search definition first. Only the `collect` command needs a YouTube Data API key in the environment (`YOUTUBE_API_KEY`). Use a new snapshot directory for a new search wave. Rerunning collection in the same directory reuses completed requests, including empty responses.

```sh
python3 scripts/collect_candidates.py plan --city delhi --year 2025 --topic street_food
python3 scripts/collect_candidates.py collect --city delhi --year 2025 --topic street_food --snapshot data/delhi_2025_street_food
python3 scripts/sample_videos.py queue data/delhi_2025_street_food
python3 scripts/screen_eligibility.py data/delhi_2025_street_food
```

Review `data/delhi_2025_street_food/screening.csv` in rank order within each city. Fill the decision, reason, reviewer and review date. For eligible videos also record the place and the evidence. Then run:

```sh
python3 scripts/sample_videos.py select data/delhi_2025_street_food --target 10
```

The last command writes `selected_10.csv`. It stops at an unresolved earlier rank. A city with fewer than ten eligible uploads after exhausting its candidates is reported as a shortfall. Extending the reviewed prefix and selecting with a larger target writes a separate manifest.

### Returned records

A successful collection returns an object conforming to [the result schema](config/result.schema.json) and writes the same object to `result.json`. Its counts describe discovery. Eligibility and the selected sample are recorded after review. Paths in `files` are relative to the snapshot folder.

| Object or table | One entry per | Fields |
| --- | --- | --- |
| `queries.json` | Planned search | Search ID, city, publication year and quarter, topic, query language, concept, duration band, exact API parameters including the expanded phrase. |
| `search_counts.csv` | Completed search, including zero-hit cells | Search design fields, phrase, number of returned hits, UTC retrieval time. |
| `search_hits.csv` | Returned hit | Search design fields, phrase, result rank, video ID, UTC retrieval time. This preserves every route by which a video was found. |
| `candidates.csv` | Distinct candidate in this city | City, video ID, watch URL, title, channel ID, publication timestamp, duration (ISO 8601), metadata status, default audio language, reported recording date and views at retrieval. Empty optional fields mean unknown. |
| `responses/*.json` | Completed API call | Requested resource, exact request parameters, retrieval timestamp and returned items. A search item identifies the video under `id.videoId` and carries a `snippet`. The enriched video item uses `id` and can carry `snippet`, `contentDetails`, `status`, `recordingDetails` and `statistics`. |
| `screening.csv` | Ranked candidate | Candidate fields plus stable rank and seed, decision, reason, place, evidence, reviewer and review date. |
| `selected_10.csv` | Eligible video selected | Completed screening row, ordered by draw rank. |

### Run acquisition and frame extraction

Use the manifest written by the selector after footage review. Python 3.11 or newer, a POSIX filesystem that supports file locking, and the [pinned video dependencies](requirements-frames.txt) are required. The output directory can live on an external drive. Keep the frame records with the search snapshot or record where to find them.

```sh
snapshot=data/delhi_2025_street_food
uv run --with-requirements requirements-frames.txt python scripts/acquire_frames.py \
  "$snapshot/selected_10.csv" "$snapshot/frames" --local-sources "$SOURCE_DIR"
```

1. **Obtain one source.** Use official YouTube Data API v3 `search.list` and `videos.list` for discovery and metadata. Use the watch link or the official embedded player for footage review. The documented public APIs provide playback and metadata and offer no general download or frame-export endpoint for another channel’s public upload. For exact frame extraction the default command reads supplied source files in place, named `VIDEO_ID.mp4`. A creator can supply an original or export their upload through Studio or Takeout. Record source availability for all selected videos. The Delhi pilot used yt-dlp, a third-party utility. A new remote download requires explicit `--allow-yt-dlp`. [YouTube video resource](https://developers.google.com/youtube/data/reference/rest/v3/videos) · [Player API](https://developers.google.com/youtube/iframe_api_reference) · [Creator exports](https://support.google.com/youtube/answer/56100)
2. **Limit disk use.** Only one source download occupies the spool at a time. The default limit per download is 256 MiB. The runner checks free space before transfer and as bytes arrive, reserving 1 GiB plus 8 MiB of working headroom during transfer. Completed JPEGs and manifests accumulate across videos. Check free space on the destination volume before the run. A low-space error pauses the queue. Resume on the same output after freeing space. Clear room or use a larger volume before changing image quality or dropping a video. Log any change to the retrieval rule.
3. **Freeze the draw.** Decode the selected video stream to establish its presentation timeline. Save the source byte count, SHA-256 checksum, duration, first presentation time, time base, software versions, seed, and requested millisecond timestamps in `frames/VIDEO_ID/plan.json`. For downloads the source record includes the rendition ID and acquisition time. PyAV returns each frame’s presentation timestamp and time base. Their product gives the display time in seconds. This matters when consecutive frames have different durations. [PyAV timing documentation](https://pyav.org/docs/stable/api/time.html)
4. **Save, verify, release.** Decode again and write one JPEG per requested moment. Each record in `complete.json` links interval, draw rank and requested time to decoded presentation timestamp, time base, file name and SHA-256. Verify that every requested moment has an image, reopen the JPEGs, and check the hashes before recording completion and deleting the downloaded source. User-supplied sources stay in place. A failed extraction keeps the downloaded source for retry. Each attempt records its ID and UTC time, configured byte limits at start, and stage and error class on failure. Rerunning checks completed records and resumes the first incomplete upload. Preserve `plan.json`, `complete.json`, the JPEGs and the run's `attempts.jsonl`. An interrupted transfer can require downloading that single rendition again.
5. **Keep the original sample visible.** A recoverable failure pauses acquisition at that ID. Record confirmed unavailability and any reserve decision against the original rank before using a revised manifest. Compare selected, acquired and lost uploads by duration, channel, language and search route. Retaining a checksum allows a future team to detect a changed source. Once a source has been released, exact re-extraction depends on obtaining those same bytes again. The saved JPEGs are the common input for coding. To expand the number of draws per interval, use a new output directory and the same seed and source bytes. The earlier draw ranks retain their timestamps.

### Coding and paper outputs

#### Frame codebook

The [coding dictionary](config/stall_frame_codebook.json) defines every field, permitted value, precedence rule and example. It drives the human instructions, Muse prompt, response schema and validation. The [six-frame blind gallery](data/delhi_2025_street_food/coding_v3/oEEO85utSZs/human_review.html) links to both human worksheets and the rendered dictionary. Version 3 assigns one label per dimension from its finite dictionary. Counts, identifiers and free-text evidence are separate from labels. The model response schema enumerates the permitted values, and the analysis validates both human and model tables against the same lists. The unit is a sighting. A person seen again in another frame receives a new frame-local ID.

| Unit | Field | Categories and use |
| --- | --- | --- |
| Frame | Setting | Street-facing stall or open market stand, restaurant interior, other public space, other setting, or unclear. A close-up of naan alone cannot establish the setting. |
| Frame | Shot composition | Food or hands close-up, person close-up, people and surroundings, wide setting, other, or unclear. Code what the image emphasizes. |
| Frame | Location relative to service | At the vendor or preparation point, on the customer side at a visibly linked queue or table, elsewhere, or unclear. This locates the focal action. |
| Frame | Quality and enumeration | Countable, partially countable, or unreadable. Record how many distinct people can be enumerated. Zero is valid in a countable frame. Partial counts are lower bounds and omitted from complete-count estimates. Unreadable counts are missing. |
| Sighting | Role | Worker, patron, clearly other, or unclear. Code visible food-service roles in any setting. Apply the stall restriction during analysis. Proximity alone leaves a person's role unclear. |
| Sighting | Apparent demographic category | Woman, man, gender unclear, clearly younger child, or age unclear. The first three cover adults and adolescents. Reuse the adult/adolescent convention from the street-photo study. Include seated diners. The denominator of the reported share comprises sightings classified as women or men. |
| Sighting | Activity | Preparing or serving, ordering/paying/receiving, eating or drinking, queuing, presenting, passing, standing or sitting, other, or unclear. Prefer a specific food action over generic posture or presentation. |

Keep observable distinctions on separate axes. At **03:45.015** in the Delhi pilot, the ladle and curry fill the shot and little identifies the setting. At **09:27.797**, someone eats at a table indoors. At **14:14.114**, someone eats at a table beside the open counter. Eating appears in both latter images. These illustrate the proposed categories and do not constitute human or Muse annotations. Gehl’s foodscape survey likewise distinguishes activities from postures. [Foodscape observation protocol](https://gehl.publiclifeapp.com/lite/observing-foodscapes/stationary-survey) · [Prior street-photo prompt](https://github.com/geosensing/mw_crowdphotos/blob/main/scripts/05_muse_count.py)

**Primary count and robustness.** Start with countable confirmed stall frames and sightings of workers and patrons. Compute `n_women / (n_women + n_men)` from the summed counts. Retain unclear gender, age and child counts alongside the denominator. Report the roles separately, then broaden to include people of uncertain role and to everyone in confirmed stall scenes. Also report all visible people across settings.

**Information supplied to coders.** Both coders label the individual JPEG. The model receives the dictionary and one image. Video ID joins each frame to the frozen publisher metadata. A future study of hosts could supply the title, channel and description in a separate pass, verify any proposed match against timestamped footage, and measure agreement. Knowing who owns the channel does not establish who appears in a particular frame. Host identification is deferred.

**Pilot decision.** The first coding round uses the six extracted frames from one selected Delhi upload. A later ten-video pilot would yield 60 frames if all are extracted. Have a human code all 60 before seeing Muse's answers, including images Muse would classify as cutaways. Report agreement on setting, missed stall scenes, and differences in worker and patron counts by apparent gender. Inspect the underlying images where the filter or a count differs. If role assignments disagree frequently, retain all people in confirmed stall scenes as a separately labeled measure and revisit the role rule before scaling. If confirmed scenes are rare, expand with the next seeded draw ranks in every pilot video. Record the change and rates of confirmed, uncertain and other scenes. Drawing until a stall or a person appears would change which videos and moments contribute.

| Paper exhibit | Denominator and source |
| --- | --- |
| Discovery and selection flow | Start with search hits, deduplicate to uploads, then count screening outcomes, selected uploads, acquisition failures and replacements. Show pending rows separately from exclusions. Use the search, screening and acquisition ledgers. |
| Footage coverage | Show selected and acquired videos by channel, reported location, search language and duration. Tabulate requested, extracted, readable, empty and unclassifiable moments by video. Use the frozen manifests and coding records. |
| Measurement check | Show agreement on the presence of people, count differences by coding category and indeterminate counts on independently coded frames. State how frames entered the check. |
| City estimates | Report videos, sampled moments, classified sightings and the ratio defined above, with video-level uncertainty and sensitivity to omission of individual channels. A city with zero classified sightings has an undefined share. |

### One-video run, November 21, 2026

The selector returned the first eligible upload in the frozen Delhi order. The first footage review used six checks in the opening 95 seconds. These moments answer the setting question for selection. The analysis draw covers the entire recording independently. The publisher lists the address and gives the upload date as April 7, 2025. The filming date is unknown.

The highest direct rendition at or below 720p was YouTube format 298, 1280 × 720 at 50 frames per second, about 372 MiB. For this pilot we used a 400 MiB download limit to screen and extract from the same source at that resolution. Free space was 23 GiB. The standard acquisition limit stays at 256 MiB. With a single local source named `oEEO85utSZs.mp4`, the commands are:

```sh
snapshot=data/delhi_2025_street_food
uv run --no-project --with-requirements requirements-frames.txt yt-dlp --no-playlist --max-filesize 400M -f 298 -o "$SOURCE_DIR/%(id)s.%(ext)s" 'https://www.youtube.com/watch?v=oEEO85utSZs'
python3 scripts/sample_videos.py select "$snapshot" --target 1
uv run --no-project --with-requirements requirements-frames.txt python scripts/acquire_frames.py "$snapshot/selected_1.csv" "$snapshot/frames" --local-sources "$SOURCE_DIR"
frames="$snapshot/frames/oEEO85utSZs"
coding="$snapshot/coding_v3/oEEO85utSZs"
python3 scripts/prepare_frame_review.py "$frames" "$coding"
```

The last command prepares a blind gallery and worksheet. To code these same frames with Muse, run the command below with the total authorized ledger cap. Each request includes one original JPEG. The client caches the raw answer and accounting entry, and checks the response against the structured output schema. The coder saves a receipt after each successful response and exports linked frame and sighting tables after all frames finish. Stop on a failed request, invalid counts, missing accounting, or the cap. A single upload can demonstrate that the stages connect and reveal coding errors. Between-video uncertainty requires more uploads.

```sh
uv run --with 'museclient @ git+https://github.com/gojiplus/museclient@2063b1bb1b58a396509b2ca0f3ca52c27138a648' python scripts/code_stall_frames.py "$frames" "$coding" --cap-usd "$PILOT_USD"
```

The [frame manifest](data/delhi_2025_street_food/frames/oEEO85utSZs/complete.json) records six verified JPEGs. The source contained 390,327,872 bytes and 977.86 seconds of video. The requested times in chronological order were 03:45.015, 04:39.636, 06:01.697, 09:27.797, 12:23.292 and 14:14.114. No people or stall filter entered the draw.

After a coder completes the two tables, run the analysis with `--coder human` or `--coder muse`. The human frame sheet requires an explicit enumerated-person count, including zero, and one matching sighting row for every person. Use consecutive person IDs beginning at one within each frame.

```sh
python3 scripts/summarize_stall_frames.py "$coding" --coder muse
```

| Stage | Script | Stored output |
| --- | --- | --- |
| Find videos | `search_plan.py`, `collect_candidates.py`, `summarize_discovery.py` | Exact queries, dated search responses, deduplicated IDs, discovery yield |
| Rank, screen and select | `sample_videos.py queue`, `screen_eligibility.py`, `sample_videos.py select` | Screening trail and ranked eligible manifest |
| Acquire and sample | `acquire_frames.py` invokes `sample_frames.py` | Source checksum, time grid, requested and displayed times, six verified JPEGs |
| Prepare blind review | `prepare_frame_review.py` | Gallery, dictionary, frame and sighting sheets, version fingerprint |
| Annotate | `code_stall_frames.py` or independent human review | One frame row and zero or more linked sightings, with raw Muse responses and spend ledger for model coding |
| Compute counts and sensitivity | `summarize_stall_frames.py` | Counts and denominators by frame and population, plus a one-video summary. Partial or unreadable observations remain visible in coverage counts. |

### Files for each city, period and topic

The collection unit is one city, one publication year and one topic. The first wave defaults to `data/<city>_<year>_<topic>/`. A repeat search with `--wave YYYY-MM-DD` writes to a separate `waves/YYYY-MM-DD/` underneath that directory. Run every downstream stage against the exact snapshot path. Initial collections and dated waves use the same internal layout. A draw name such as `pilot1` identifies the reviewed selection within a wave. The exporter fingerprints the collection from the planned queries, dated search counts and all returned hits, and fingerprints the selected manifest separately.

| Location inside each snapshot | Unit and link |
| --- | --- |
| `queries.json`, `responses/`, `search_counts.csv` | Planned API requests, dated returned items and counts, including zero hits. |
| `search_hits.csv` | One row per query result, including exact keyword phrase, its language, quarter, duration band, rank, video ID and retrieval time. Preserve every route even when a video appears repeatedly. |
| `candidates.csv`, `video_metadata.jsonl` | One row per unique candidate. The JSONL export includes video ID, URL, title, description, tags, category, channel ID and name, publication timestamp, duration, publisher-provided language, recording date and location when present, engagement counts, status, technical details, retrieval time and pointer to the original API response. Null means unavailable. Views, likes and comments are dated observations. Search city and filming location are distinct fields. |
| `screening.csv`, `machine_screening.csv`, `resolved_screening.csv`, `selected_N.csv` | One candidate or selected video per row with rank, decision, evidence and seed. Preserve the selected manifest for each draw. |
| `frames/VIDEO_ID/` | Draw plan, exact source version, original sampled JPEGs and extraction receipts. Store the frame set once per video draw and reuse the verified images across coders. |
| `coding_v3/VIDEO_ID/` | Human and Muse outputs, frozen dictionary and response schema, image hashes and accounting. A new codebook receives a new directory. |
| `analysis/DRAW/CODER/` | A self-describing bundle named `CITY_YEAR_TOPIC_DRAW_CODER_frames.csv`, `…_video_coverage.csv` and `…_discovery_hits.csv`. Stack the same file type across cities or waves. Keep collection ID and draw in pooled data. Join discovery hits to videos for search analysis. Joining them directly to frame observations would count videos once for every search that found them. |

For the Delhi pilot, `Delhi street food` found the selected upload at rank 25 and `दिल्ली स्ट्रीट फूड` at rank 6 in the second quarter, medium-duration band. Both occurrences survive in the [discovery export](data/delhi_2025_street_food/analysis/pilot1/muse/delhi_2025_street_food_pilot1_muse_discovery_hits.csv). The [metadata row schema](config/video_metadata.schema.json) specifies the retained fields and their types. Official metadata includes an audio language for 846 of 1,205 candidates, coordinates for 229, and a recording date for 16. Use publication year to define the search cohort. The selected video was published April 7, 2025, by Shoaib Arora. The November snapshot recorded 38,077 views, 753 likes and 26 comments. Its filming date and coordinates were missing.

### Analysis-ready records and inference

```sh
python3 scripts/build_analysis_frames.py "$snapshot" "$snapshot/selected_1.csv" --draw pilot1 --coding "$coding" --coder muse
```

Supply all available coding directories for that draw after `--coding`. The builder starts from each selected video's frozen moments and joins exactly one coder. Every planned moment stays in the frame table even if extraction or coding failed. The [coverage file](data/delhi_2025_street_food/analysis/pilot1/muse/delhi_2025_street_food_pilot1_muse_video_coverage.csv) retains selected videos with no moment plan. Inspect coverage before analysis. Compare human and model outputs by frame ID; pooling both coders as separate sampled moments would double the sample.

The [Delhi frame table](data/delhi_2025_street_food/analysis/pilot1/muse/delhi_2025_street_food_pilot1_muse_frames.csv) has one row per requested moment. Video and channel IDs are stable string cluster keys. Rows include requested time (milliseconds and clock time), elapsed display time in seconds, integer presentation timestamp and its time base, source and JPEG hashes, interval and draw rank, exact interval grid size, and coding status. The watch link seeks to the preceding whole second for manual inspection. For instance, 03:45.015 mapped to a frame starting at 225.000 seconds. `sample_seed` in the selection records the video draw; `frame_seed` in the export records the time draw.

The primary columns count apparent women and men among stall workers and patrons. A countable frame with no people or a clearly different setting contributes zero to that tally. A partially countable or unreadable frame, a missing annotation or an uncertain setting with visible people gives a missing primary count. Other scopes have their own count columns. Keep `primary_n_classified` as the denominator. Estimate a share from the ratio of weighted sums. The within-video weight is the fraction of the millisecond grid in the interval divided by the number of draws from it. It sums to one in a complete video. `p_moment_given_video` is the conditional time-draw probability. Discovery does not supply a citywide inclusion probability. Report attrition and sensitivity to incomplete videos separately.

For a multi-video estimate, allow observations in a video to be dependent. For sensitivity to repeated uploads by the same creator, cluster by channel across that creator’s videos. Each video belongs to one channel. Report the number of independent clusters for the chosen analysis. The six observations here come from one video and one channel, so between-cluster uncertainty cannot be estimated. Muse returned six schema-valid annotations for an estimated $0.00260045 from reported token usage. Human validation remains pending.

### Maintaining this record

For each new city, year or topic, add a dated run entry with the snapshot path, code revision, configuration, seeds, what ran, exclusions or failures, and links to the records behind reported totals. Record changes to keywords, geography, screening rules, acquisition settings, frame sampling or coding with the rationale, date, and affected ranks. Preserve the earlier snapshot and decisions. Build paper tables from these records so that a later reader can trace a reported number back to its uploads and frames.
