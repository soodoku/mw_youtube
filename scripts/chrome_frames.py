"""Capture the displayed pixels of a public YouTube watch page in an isolated Chrome session."""

import argparse
import base64
import csv
import json
import re
import time
from contextlib import contextmanager
from pathlib import Path

from playwright.sync_api import sync_playwright


def duration_seconds(iso):
    match = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?", iso)
    if not match:
        raise ValueError(f"Unsupported API duration {iso}")
    h, m, s = (float(n or 0) for n in match.groups())
    return h * 3600 + m * 60 + s


@contextmanager
def player():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome", headless=False)
        try:
            yield browser.new_page(viewport={"width": 1280, "height": 800})
        finally:
            browser.close()


def content_video(page, expected):
    """Wait for the actual recording, including ordinary pre-roll playback."""
    end = time.monotonic() + 95
    video = page.locator("video:visible").first
    while time.monotonic() < end:
        skip = page.get_by_role(
            "button", name=re.compile(r"^Skip(?: Ads?| video ads?)?$", re.I)
        ).first
        if skip.is_visible():
            skip.click(timeout=2000)
        if video.count():
            state = video.evaluate(
                """v=>{v.muted=true;v.play().catch(()=>{});
              return [Number.isFinite(v.duration)?v.duration:0,v.readyState,v.videoWidth,
              !!v.closest('.ad-showing,.ad-interrupting')]}"""
            )
            if (
                abs(state[0] - expected) <= 2
                and state[1] >= 2
                and state[2]
                and not state[3]
            ):
                return video
        page.wait_for_timeout(400)
    raise ValueError("Selected content did not become playable within 95 seconds")


def watch(page, vid, expected):
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", vid):
        raise ValueError("Invalid video ID")
    page.goto(
        "https://www.youtube.com/watch?v=" + vid,
        wait_until="domcontentloaded",
        timeout=35000,
    )
    video = content_video(page, expected)
    duration = video.evaluate("v=>{v.pause();return v.duration}")
    if abs(duration - expected) > 2 or vid not in page.url:
        raise ValueError("Player does not match the selected upload and API duration")
    return video, duration


def capture(video, seconds, path):
    page = video.page
    expected = video.evaluate("v=>v.duration")
    target = page.url.split("&t=")[0]
    if "watch?v=" not in target:
        raise ValueError("Expected canonical watch page")
    # Timestamped watch links let the player buffer close to the sampled instant.
    page.goto("about:blank")
    page.goto(
        target + "&t=" + str(int(seconds)) + "s",
        wait_until="domcontentloaded",
        timeout=35000,
    )
    video = content_video(page, expected)

    # A completed media seek followed by repaint yields displayed pixels; the player
    # time is an observation from Chrome rather than a decoder presentation timestamp.
    frame = video.evaluate(
        """async (v,t) => {
      v.pause();
      if (Math.abs(v.currentTime-t)>0.001 || v.seeking) {
        await new Promise((resolve,reject) => {
          const timer=setTimeout(()=>reject(Error('Media seek timed out')),30000);
          v.addEventListener('seeked',()=>{clearTimeout(timer);resolve()}, {once:true});
          v.currentTime=t;
        });
      }
      v.pause();
      await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
      if(v.readyState<2 || v.seeking) throw Error('No rendered media after seek');
      const c=document.createElement('canvas'); c.width=v.videoWidth;c.height=v.videoHeight;
      c.getContext('2d').drawImage(v,0,0);
      return {t:v.currentTime,jpeg:c.toDataURL('image/jpeg',0.9).split(',')[1]};
    }""",
        seconds,
    )
    if (
        video.evaluate("v=>!!v.closest('.ad-showing,.ad-interrupting')")
        or abs(video.evaluate("v=>v.duration") - expected) > 0.1
    ):
        raise ValueError("Content changed while capturing")
    if abs(frame["t"] - seconds) > 0.15:
        raise ValueError(f"Player displayed {frame['t']}s for requested {seconds}s")
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(base64.b64decode(frame["jpeg"], validate=True))
    tmp.replace(path)
    return frame["t"]


def review(snapshot, out, first, last):
    out.mkdir(parents=True, exist_ok=True)
    with (snapshot / "screening.csv").open(newline="") as f:
        rows = list(csv.DictReader(f))
    with player() as page:
        for row in rows:
            rank = int(row["video_rank"])
            if not first <= rank <= last or row["decision"] in {
                "excluded",
                "unavailable",
            }:
                continue
            vid = row["video_id"]
            folder = out / f"{rank:04d}_{vid}"
            folder.mkdir(exist_ok=True)
            if (folder / "review.json").exists():
                continue
            try:
                video, duration = watch(page, vid, duration_seconds(row["duration"]))
                moments = []
                for i, fraction in enumerate((0.03, 0.20, 0.45, 0.68, 0.88)):
                    t = duration * fraction
                    file = f"review_{i}.jpg"
                    displayed = capture(video, t, folder / file)
                    moments.append(
                        dict(file=file, requested_s=t, displayed_s=displayed)
                    )
                record = dict(
                    video_id=vid, rank=rank, watch_url=row["watch_url"], moments=moments
                )
                (folder / "review.json").write_text(json.dumps(record, indent=2) + "\n")
                print(rank, vid, "ready", flush=True)
            except Exception as exc:
                print(
                    rank,
                    vid,
                    type(exc).__name__,
                    str(exc).splitlines()[0][:160],
                    flush=True,
                )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Prepare footage evidence for ranked eligibility review"
    )
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--first", type=int, required=True)
    parser.add_argument("--last", type=int, required=True)
    args = parser.parse_args()
    review(args.snapshot, args.output, args.first, args.last)
