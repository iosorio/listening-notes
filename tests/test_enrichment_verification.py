"""Integrity checks must accept reviewed enrichment and reject unrecorded edits."""

import json
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts.radar_verification import verify_temporary_materialization
from scripts.verify_discovery_provenance_backfill import replay_processed_intake, processed_enrichment_in_order
from scripts.enrichment_common import EnrichmentError
from scripts.merge_enrichment_patches import merge
from tests import test_enrichment_pipeline as fixtures


class EnrichmentVerificationTest(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name).resolve()
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.name", "RADAR Test"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.email", "radar@example.invalid"], cwd=self.root, check=True)
        _, self.research, self.canonical, self.curated, self.processed = fixtures.EnrichmentMergeTest().fixture(self.root, [fixtures.complete_patch()])
        self.baseline = json.loads(self.canonical.read_text())
        self.commit()

    def commit(self):
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "reviewed test inputs"], cwd=self.root, check=True)

    def ingest(self):
        merge([self.curated], False, self.canonical, self.processed, self.root, self.research)
        return self.processed / self.curated.name

    def test_reviewed_enrichment_is_an_exact_temporary_materialization(self):
        self.ingest()
        result = verify_temporary_materialization(self.root)
        self.assertEqual(result["enrichment_batches"], 1)
        self.assertEqual(result["added_candidates"], 0)
        self.assertEqual(set(result["changed_paths"]), {
            "radar/events.json", "radar/inbox/curated/enrichment/test.json", "radar/inbox/processed/enrichment/test.json",
        })

    def test_rewritten_archive_is_rejected(self):
        archived = self.ingest()
        archived.write_bytes(archived.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "does not preserve its committed source"):
            verify_temporary_materialization(self.root)

    def test_unreviewed_research_edit_is_rejected(self):
        self.ingest()
        research = self.research / "test.json"
        research.write_bytes(research.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "unauthorized path set"):
            verify_temporary_materialization(self.root)

    def test_unrecorded_canonical_change_is_rejected_after_enrichment(self):
        self.ingest()
        current = json.loads(self.canonical.read_text())
        current["events"][0]["artist"] = "Unreviewed replacement"
        self.canonical.write_text(json.dumps(current))
        with self.assertRaisesRegex(ValueError, "does not match deterministic materialization"):
            verify_temporary_materialization(self.root)

    def test_backfill_replays_enrichment_without_weakening_protected_fields(self):
        archived = self.ingest()
        current = json.loads(self.canonical.read_text())
        with patch("scripts.verify_discovery_provenance_backfill.ROOT", self.root):
            result = replay_processed_intake(self.baseline, current, [], [archived])
            self.assertEqual(result["enrichment_batches"], 1)
            current["events"][0]["priority"] = "A"
            with self.assertRaisesRegex(ValueError, "does not match"):
                replay_processed_intake(self.baseline, current, [], [archived])

    def test_backfill_rejects_altered_research_hash(self):
        archived = self.ingest()
        research = self.research / "test.json"
        research.write_bytes(research.read_bytes() + b" ")
        with patch("scripts.verify_discovery_provenance_backfill.ROOT", self.root), self.assertRaisesRegex(EnrichmentError, "SHA-256"):
            replay_processed_intake(self.baseline, json.loads(self.canonical.read_text()), [], [archived])

    def test_processed_history_order_is_not_filename_order(self):
        # First archive is z, the second is a; both preserve published sources.
        original = self.curated.read_bytes()
        z = self.curated.with_name("z.json")
        z.write_bytes(original)
        self.curated.unlink()
        self.commit()
        self.processed.mkdir(parents=True)
        z.rename(self.processed / z.name)
        self.commit()
        a = z.with_name("a.json")
        a.write_bytes(original)
        self.commit()
        a.rename(self.processed / a.name)
        self.commit()
        with patch("scripts.verify_discovery_provenance_backfill.ROOT", self.root):
            self.assertEqual([p.name for p in processed_enrichment_in_order()], ["z.json", "a.json"])
            baseline = subprocess.check_output(["git", "rev-parse", "HEAD~2"], cwd=self.root, text=True).strip()
            self.assertEqual([p.name for p in processed_enrichment_in_order(baseline)], ["a.json"])
            (self.processed / "a.json").write_bytes(original + b" ")
            with self.assertRaisesRegex(ValueError, "published curated source"):
                processed_enrichment_in_order()


if __name__ == "__main__":
    unittest.main()
