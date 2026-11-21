import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import chrome_frames as chrome  # noqa: E402


class SignedInCapture(unittest.TestCase):
    def test_uses_default_context_and_only_closes_owned_tab(self):
        with patch.object(chrome, "sync_playwright") as start:
            chromium = start.return_value.__enter__.return_value.chromium
            browser = chromium.connect_over_cdp.return_value
            context = MagicMock()
            browser.contexts = [context]
            with patch.dict("os.environ", {"MW_YOUTUBE_CHROME_PORT": "9223"}):
                with chrome.player() as tab:
                    self.assertIs(tab, context.new_page.return_value)
            chromium.connect_over_cdp.assert_called_once_with(
                "ws://127.0.0.1:9223/devtools/browser", no_defaults=True, timeout=90000
            )
            chromium.launch.assert_not_called()
            tab.close.assert_called_once()
            browser.close.assert_not_called()

    def test_missing_premium_marker_stops_before_media_access(self):
        page = MagicMock()
        page.locator.return_value.first.wait_for.side_effect = chrome.PlaywrightError(
            "Missing logo"
        )
        with patch.object(chrome, "content_video") as video:
            with self.assertRaisesRegex(RuntimeError, "Premium masthead"):
                chrome.watch(page, "ZmBfCcLxi2c", 563)
            video.assert_not_called()

    def test_failed_content_verification_keeps_previous_jpeg(self):
        page = MagicMock()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "moment.jpg"
            path.write_bytes(b"previous frame")
            with patch.object(chrome, "content_video") as video:
                video.return_value.evaluate.side_effect = chrome.PlaywrightError(
                    "Selected upload could not be verified at capture"
                )
                with self.assertRaises(chrome.PlaywrightError):
                    chrome.capture(page, "ZmBfCcLxi2c", 563, 254.993, path)
            self.assertEqual(path.read_bytes(), b"previous frame")
