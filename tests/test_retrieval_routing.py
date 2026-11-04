import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("retrieve_yuliao", ROOT / "scripts" / "retrieve_yuliao.py")
retriever = importlib.util.module_from_spec(spec)
spec.loader.exec_module(retriever)

class RetrievalAndRegistryTests(unittest.TestCase):
    def test_unmatched_popular_record_does_not_score(self):
        record = {"topics": [], "title": "普通标题", "opening": "", "copy": "其他内容", "engagement_value": 100000}
        self.assertEqual(retriever.score_record(record, ["无关关键词"])[0], 0)

    def test_relevant_popular_record_scores(self):
        record = {"topics": [], "title": "盆栽养护", "opening": "", "copy": "其他内容", "engagement_value": 100000}
        self.assertGreater(retriever.score_record(record, ["盆栽"])[0], 0)

    def test_registry_lists_real_unique_skills_and_handoffs(self):
        run = subprocess.run([sys.executable, str(ROOT / "skills" / "dpjf" / "scripts" / "list-skills.py")], capture_output=True, text=True, encoding="utf-8", check=True)
        result = json.loads(run.stdout)
        names = {item["name"] for item in result["skills"]}
        self.assertEqual(names, {"dpjf-plan", "dpjf-benchmark", "dpjf-topic", "dpjf-title", "dpjf-script", "dpjf-creative", "dpjf-homework", "dpjf-review", "dpjf-communication", "dpjf-patrol", "dpjf-recap", "dpjf-growth", "dpjf-learning", "dpjf-student", "dpjf-update"})
        self.assertFalse(result["errors"])
        for item in result["skills"]:
            self.assertTrue(Path(item["source"]).is_file())
            self.assertTrue(any("不交出" in line for line in item["handoff"]))

if __name__ == "__main__":
    unittest.main()
