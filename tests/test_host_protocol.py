import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import code_stall_frames as code  # noqa: E402

from mw_youtube.codebook import CONTEXT_BOOK, book_sha, schema  # noqa: E402
from mw_youtube.counts import summarize  # noqa: E402


class HostProtocol(unittest.TestCase):
    def test_vendor_can_host_and_indeterminate_host_remains_separate(self):
        fields = dict(video_id="fixture0001", interval=0, rank=1)
        groups = [
            ("vendor", "woman", "apparent_host"),
            ("patron", "man", "not_host"),
            ("vendor", "man", "unclear"),
        ]
        people = [
            dict(
                **fields,
                person_id=i,
                role=r,
                group=g,
                host_status=h,
                activity="presenting",
                cue="At the service window",
            )
            for i, (r, g, h) in enumerate(groups, 1)
        ]
        frame = dict(
            **fields,
            quality="countable",
            n_enumerated=3,
            setting="street_stall",
            shot="people_and_surroundings",
            service_area="at_vendor",
            evidence="Stall",
        )
        counts = {
            r["scope"]: (r["n_women"], r["n_men"])
            for r in summarize([frame], people, CONTEXT_BOOK)
        }
        self.assertEqual(counts["vendor"], (1, 1))
        self.assertEqual(counts["worker_and_patron"], (1, 2))
        self.assertEqual(counts["worker_and_patron_without_apparent_hosts"], (0, 2))
        self.assertEqual(counts["worker_and_patron_confirmed_nonhosts"], (0, 1))
        self.assertEqual(counts["apparent_host"], (1, 0))

    def test_exact_context_sent_and_bound_to_cache(self):
        mock = MagicMock()
        answer = dict(
            quality="countable",
            n_enumerated=0,
            setting="unclear",
            shot="food_or_hands_closeup",
            service_area="unclear",
            evidence="Plate",
            sightings=[],
        )
        client = mock.Client.return_value
        client.complete.return_value = (answer, Path("test-call"))
        client.spend.return_value = {}
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.dict(sys.modules, museclient=mock),
        ):
            root = Path(tmp)
            ctx = dict.fromkeys(CONTEXT_BOOK["context_fields"])
            ctx.update(
                video_id="fixture0001",
                title="Publisher title",
                channel_title="Test channel",
            )
            body = json.dumps(ctx)
            (root / "video_context.json").write_text(body)
            (root / "codebook.json").write_text(json.dumps(CONTEXT_BOOK))
            (root / "frame.jpg").write_bytes(b"fixture")
            row = dict(
                video_id=ctx["video_id"],
                interval=0,
                rank=1,
                requested_ms=200,
                jpeg="frame.jpg",
                sha256="frozen",
            )
            digest = hashlib.sha256(body.encode()).hexdigest()
            (root / "review_manifest.json").write_text(
                json.dumps(
                    dict(
                        codebook_sha256=book_sha(CONTEXT_BOOK),
                        frames=[row],
                        video_context_sha256=digest,
                    )
                )
            )
            with patch.object(code, "prepare", return_value=[row]):
                code.run(root, root, 1)
                args, kw = client.complete.call_args
                self.assertIn(body, args[0][0]["content"][0]["text"])
                self.assertEqual(args[1], schema(CONTEXT_BOOK))
                self.assertEqual(kw["key_extra"]["context_sha256"], digest)
                (root / "video_context.json").write_text(body + " ")
                with self.assertRaisesRegex(ValueError, "manifest"):
                    code.run(root, root, 1)
            self.assertEqual(client.complete.call_count, 1)
