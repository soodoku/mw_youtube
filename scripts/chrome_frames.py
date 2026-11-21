"""Capture sampled video frames in an existing YouTube Premium Chrome session."""

import argparse
import base64
import csv
import json
import os
import re
import time
from contextlib import contextmanager
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
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
        port = int(os.environ.get("MW_YOUTUBE_CHROME_PORT", "9222"))
        if not 1 <= port <= 65535:
            raise ValueError("Invalid Chrome port")
        # Chrome's approval-only endpoint presents its own consent dialog.
        endpoint = f"ws://127.0.0.1:{port}/devtools/browser"
        try:
            browser = pw.chromium.connect_over_cdp(
                endpoint, no_defaults=True, timeout=90000
            )
        except PlaywrightError as exc:
            raise RuntimeError(
                "Open chrome://inspect/#remote-debugging in your Premium Chrome profile, "
                "enable remote debugging, and allow the connection in Chrome."
            ) from exc
        page = browser.contexts[0].new_page()
        try:
            yield page
        finally:
            page.close()


def require_premium(page):
    # The membership logo is public UI. No account identifiers enter the ledger.
    logo = page.locator(
        "#masthead #logo[aria-label*='premium' i], #masthead #logo[title*='premium' i], "
        "#masthead #logo [aria-label*='premium' i], #masthead #logo [title*='premium' i], "
        "#masthead #logo [icon*='premium' i], #masthead #logo svg title:text-matches('Premium','i')"
    ).first
    try:
        logo.wait_for(state="attached", timeout=12000)
    except PlaywrightError as exc:
        raise RuntimeError(
            "YouTube did not show its Premium masthead in the attached tab. "
            "Check the Chrome profile and the active YouTube membership."
        ) from exc


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
    require_premium(page)
    video = content_video(page, expected)
    duration = video.evaluate("v=>{v.pause();return v.duration}")
    if abs(duration - expected) > 2 or vid not in page.url:
        raise ValueError("Player does not match the selected upload and API duration")
    return duration


def capture(page, vid, expected, seconds, path):
    target = "https://www.youtube.com/watch?v=" + vid
    # Timestamped watch links let the player buffer close to the sampled instant.
    page.goto("about:blank")
    page.goto(
        target + "&t=" + str(int(seconds)) + "s",
        wait_until="domcontentloaded",
        timeout=35000,
    )
    require_premium(page)
    video = content_video(page, expected)

    # A completed media seek followed by repaint yields displayed pixels; the player
    # time is an observation from Chrome rather than a decoder presentation timestamp.
    frame = video.evaluate(
        """async (v,[t,expectedId,expectedDuration]) => {
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
      const player = v.closest('#movie_player');
      const url = player?.getVideoUrl?.();
      if (!url || new URL(url, location.href).searchParams.get('v') !== expectedId ||
          player.matches('.ad-showing,.ad-interrupting') ||
          !Number.isFinite(v.duration) || Math.abs(v.duration - expectedDuration) > 0.1)
        throw Error('Selected upload could not be verified at capture');
      const c=document.createElement('canvas'); c.width=v.videoWidth;c.height=v.videoHeight;
      c.getContext('2d').drawImage(v,0,0);
      return {t:v.currentTime,jpeg:c.toDataURL('image/jpeg',0.9).split(',')[1]};
    }""",
        [seconds, vid, expected],
    )
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
                duration = watch(page, vid, duration_seconds(row["duration"]))
                moments = []
                for i, fraction in enumerate((0.03, 0.20, 0.45, 0.68, 0.88)):
                    t = duration * fraction
                    file = f"review_{i}.jpg"
                    displayed = capture(page, vid, duration, t, folder / file)
                    moments.append(
                        dict(file=file, requested_s=t, displayed_s=displayed)
                    )
                record = dict(
                    video_id=vid,
                    rank=rank,
                    watch_url=row["watch_url"],
                    moments=moments,
                    browser_session="attached_premium",
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
