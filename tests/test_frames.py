import csv
import io
import json
import shutil
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch

import av
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import acquire_frames as acquire  # noqa: E402
from sample_frames import displayed_frames, draw, presentation, timeline  # noqa: E402


def make_clip(path):
    # Known colors and deliberately uneven timing give an independent pixel/time oracle.
    with av.open(str(path), "w") as container:
        stream = container.add_stream("mpeg4", rate=5)
        stream.width, stream.height, stream.pix_fmt = 160, 100, "yuv420p"
        for tick, color in zip(
            (0, 1, 4, 7, 11), ("red", "green", "blue", "yellow", "purple")
        ):
            frame = av.VideoFrame.from_image(Image.new("RGB", (160, 100), color))
            frame.pts, frame.time_base = tick, Fraction(1, 5)
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)


class AcquisitionTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.ids = ["fixture0001", "fixture0002"]
        self.clip = self.root / "fixture0001.mp4"
        make_clip(self.clip)
        self.manifest = self.root / "selected_2.csv"
        with self.manifest.open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["video_id", "decision"])
            writer.writerows((vid, "eligible") for vid in self.ids)
        self.out = self.root / "frames"

    def test_known_variable_frame_times(self):
        origin, end, _ = timeline(self.clip)
        self.assertEqual((origin, end), (0, Fraction(12, 5)))
        times = (0, 199, 200, 799, 800, 2199, 2200, 2399)
        actual = [
            (presentation(frame), frame.to_image().getpixel((50, 50)))
            for _, frame in displayed_frames(
                self.clip, origin, [{"requested_ms": t} for t in times]
            )
        ]
        self.assertEqual(
            [int(t * 1000) for t, _ in actual], [0, 0, 200, 200, 800, 1400, 2200, 2200]
        )
        self.assertGreater(actual[4][1][2], 230)
        small, large = (draw(self.ids[0], 123, end, n) for n in (2, 3))
        self.assertEqual(small, [r for r in large if r["rank"] <= 2])
        self.assertEqual(len(set(r["requested_ms"] for r in small)), 6)

    def test_resume_retains_only_interrupted_source(self):
        downloaded = []

        def fetch(vid, spool, cap, reserve):
            self.assertEqual(list(spool.glob("*.video")), [])
            downloaded.append(vid)
            dest = spool / (vid + ".video")
            shutil.copyfile(self.clip, dest)
            acquire.dump(spool / (vid + ".json"), {"format_id": "test"})
            return dest

        real = acquire.extract

        def fail_second(source, folder, vid, *args):
            if vid == self.ids[1]:
                raise RuntimeError("fixture interruption")
            real(source, folder, vid, *args)

        with patch.object(acquire, "download", side_effect=fetch):
            with patch.object(acquire, "extract", side_effect=fail_second):
                with self.assertRaises(RuntimeError):
                    acquire.run(self.manifest, self.out, reserve=0, allow_yt_dlp=True)
            self.assertEqual(
                [p.stem for p in (self.out / "spool").glob("*.video")], self.ids[1:]
            )
            acquire.run(self.manifest, self.out, reserve=0, allow_yt_dlp=True)
            acquire.run(self.manifest, self.out, reserve=0, allow_yt_dlp=True)
        self.assertEqual(downloaded, self.ids)
        self.assertEqual(list((self.out / "spool").iterdir()), [])
        f = self.out / self.ids[0] / "i0_r1.jpg"
        f.write_bytes(b"corrupt")
        with self.assertRaisesRegex(ValueError, "Changed JPEG"):
            acquire.run(self.manifest, self.out, reserve=0, allow_yt_dlp=True)

    def test_transfer_cap_and_short_response(self):
        vid = self.ids[0]
        raw = self.clip.read_bytes()
        info = {
            "id": vid,
            "protocol": "https",
            "format_id": "test",
            "url": "https://example.org/test",
        }
        with patch.object(acquire, "YoutubeDL") as resolver:
            resolver.return_value.__enter__.return_value.extract_info.return_value = (
                info
            )
            for limit, declared, success in [
                (5, None, False),
                (len(raw) + 1, len(raw) + 1, False),
                (len(raw), len(raw), True),
            ]:
                response = io.BytesIO(raw)
                response.headers = {"Content-Length": str(declared)} if declared else {}
                with patch.object(acquire, "urlopen", return_value=response):
                    if success:
                        self.assertEqual(
                            acquire.download(vid, self.root, limit, 0).read_bytes(), raw
                        )
                    else:
                        with self.assertRaises((ValueError, IOError)):
                            acquire.download(vid, self.root, limit, 0)
                        self.assertFalse((self.root / (vid + ".video")).exists())
                    self.assertFalse((self.root / (vid + ".part")).exists())

    def test_unresolved_and_low_disk_do_not_fetch(self):
        with patch.object(acquire, "download") as fetch:
            with self.assertRaises(OSError):
                acquire.run(self.manifest, self.out, reserve=2**60)
            self.manifest.write_text("video_id,decision\nfixture0001,unclear\n")
            with self.assertRaisesRegex(ValueError, "unresolved"):
                acquire.run(self.manifest, self.out, reserve=0)
            fetch.assert_not_called()
        events = [
            json.loads(s)
            for s in (self.out / "attempts.jsonl").read_text().splitlines()
        ]
        self.assertEqual([e["status"] for e in events], ["started", "failed"])
