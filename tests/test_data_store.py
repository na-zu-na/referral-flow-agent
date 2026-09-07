import json
import tempfile
import unittest
from pathlib import Path

from tools.data_store import DataStoreError, clear_cache, load_object, load_table


class DataStoreTests(unittest.TestCase):
    def tearDown(self):
        clear_cache()

    def test_bundled_problem_b_data_loads(self):
        self.assertEqual(len(load_table("referrals")), 80)
        self.assertEqual(len(load_table("specialties")), 5)
        self.assertEqual(load_object("as_of"), {"as_of": "2026-09-09"})

    def test_callers_cannot_mutate_cached_data(self):
        rows = load_table("referrals")
        rows[0]["referral_id"] = "CHANGED"

        self.assertNotEqual(load_table("referrals")[0]["referral_id"], "CHANGED")

    def test_unknown_dataset_is_rejected(self):
        with self.assertRaises(DataStoreError) as caught:
            load_table("claims")

        self.assertEqual(caught.exception.code, "UNKNOWN_DATASET")

    def test_missing_and_invalid_files_have_stable_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(DataStoreError) as missing:
                load_table("referrals", root)
            self.assertEqual(missing.exception.code, "DATA_FILE_NOT_FOUND")

            (root / "referrals.json").write_text("not json", encoding="utf-8")
            with self.assertRaises(DataStoreError) as invalid:
                load_table("referrals", root)
            self.assertEqual(invalid.exception.code, "DATA_INVALID_JSON")

    def test_wrong_top_level_shape_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "referrals.json").write_text(
                json.dumps({"referral_id": "REF-1"}), encoding="utf-8"
            )

            with self.assertRaises(DataStoreError) as caught:
                load_table("referrals", root)

        self.assertEqual(caught.exception.code, "DATA_INVALID_SHAPE")


if __name__ == "__main__":
    unittest.main()
