from pathlib import Path
import unittest

from sl_emails.domain.email_presets import CURATED_ICON_GROUPS
from sl_emails.domain.iconography import ICON_REGISTRY


class IconographyTests(unittest.TestCase):
    def test_every_registered_icon_has_a_local_svg_asset(self):
        icons_dir = Path(__file__).resolve().parents[1] / "src" / "sl_emails" / "web" / "static" / "icons"

        missing = [entry["filename"] for entry in ICON_REGISTRY.values() if not (icons_dir / entry["filename"]).exists()]

        self.assertEqual(missing, [])

    def test_every_registered_icon_has_a_firebase_hosting_asset(self):
        icons_dir = Path(__file__).resolve().parents[1] / "firebase-hosting" / "static" / "icons"

        missing = [entry["filename"] for entry in ICON_REGISTRY.values() if not (icons_dir / entry["filename"]).exists()]

        self.assertEqual(missing, [])

    def test_every_curated_icon_option_maps_to_a_registered_icon(self):
        option_values = [
            option["value"]
            for group in CURATED_ICON_GROUPS
            for option in group.get("options", [])
        ]

        self.assertTrue(option_values)
        self.assertTrue(all(value in ICON_REGISTRY for value in option_values))


if __name__ == "__main__":
    unittest.main()
