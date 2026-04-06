import unittest

from sl_emails.services.signage_store import MemorySignageStore, normalize_signage_day_payload


class SignageStoreTests(unittest.TestCase):
    def test_normalize_signage_day_payload_preserves_existing_fields_when_missing(self):
        store = MemorySignageStore()
        created = store.save_day(
            "2026-03-23",
            {
                "events": [{"title": "Varsity Soccer", "date": "2026-03-23"}],
                "source_summary": {"athletics_events": 1, "arts_events": 0, "total_events": 1},
                "metadata": {"ingest": {"status": "success"}},
            },
        )

        normalized = normalize_signage_day_payload(
            "2026-03-23",
            {"metadata": {"manual": {"status": "ok"}}},
            existing=created,
        )

        self.assertEqual(len(normalized.events), 1)
        self.assertEqual(normalized.source_summary["total_events"], 1)
        self.assertEqual(normalized.metadata["manual"]["status"], "ok")
        self.assertEqual(normalized.created_at, created.created_at)

    def test_memory_store_updates_metadata_recursively(self):
        store = MemorySignageStore()
        store.save_day(
            "2026-03-23",
            {
                "events": [{"title": "Varsity Soccer", "date": "2026-03-23"}],
                "source_summary": {"athletics_events": 1, "arts_events": 0, "total_events": 1},
                "metadata": {"ingest": {"status": "success", "actor": "system"}},
            },
        )

        updated = store.update_day_metadata(
            "2026-03-23",
            {"ingest": {"status": "failed", "message": "source unavailable"}},
        )

        self.assertEqual(updated.metadata["ingest"]["status"], "failed")
        self.assertEqual(updated.metadata["ingest"]["actor"], "system")
        self.assertEqual(updated.metadata["ingest"]["message"], "source unavailable")


if __name__ == "__main__":
    unittest.main()
