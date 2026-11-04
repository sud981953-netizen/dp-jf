import importlib.util
import io
import json
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "skills" / "dpjf"
SKILLS = {
    "dpjf-plan", "dpjf-benchmark", "dpjf-topic", "dpjf-title", "dpjf-script",
    "dpjf-creative", "dpjf-homework", "dpjf-review", "dpjf-communication",
    "dpjf-patrol", "dpjf-recap", "dpjf-growth", "dpjf-learning",
    "dpjf-student", "dpjf-update",
}


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PackageTests(unittest.TestCase):
    def test_catalog_discovers_all_unique_actual_skills(self):
        run = subprocess.run([sys.executable, str(MAIN / "scripts" / "list-skills.py")], capture_output=True, text=True, encoding="utf-8", check=True)
        value = json.loads(run.stdout)
        self.assertFalse(value["errors"])
        self.assertEqual({x["name"] for x in value["skills"]}, SKILLS)
        for item in value["skills"]:
            self.assertTrue(Path(item["source"]).is_file())
            self.assertTrue(any(x.startswith("不交出：") for x in item["handoff"]))

    def test_registry_rejects_invalid_name_and_missing_file(self):
        module = load_module("discover", MAIN / "scripts" / "list-skills.py")
        with self.assertRaises(ValueError):
            module.read_entry("../outside")
        with self.assertRaises(ValueError):
            module.read_entry("dpjf-does-not-exist")

    def test_all_local_markdown_references_exist(self):
        for skill in (ROOT / "skills").iterdir():
            if not skill.is_dir():
                continue
            for document in skill.rglob("*.md"):
                for target in re.findall(r"\]\(([^)#]+)(?:#[^)]*)?\)", document.read_text(encoding="utf-8")):
                    if "://" in target or target.startswith("/"):
                        continue
                    self.assertTrue((document.parent / target).exists(), f"{document}: {target}")

    def test_each_business_skill_has_dedicated_resource_contract(self):
        for folder in (ROOT / "skills").glob("dpjf-*"):
            for name in ("SKILL.md", "references/资源调用.md"):
                path = folder / name
                self.assertTrue(path.is_file(), str(path))
                self.assertTrue(path.read_text(encoding="utf-8").strip(), str(path))

    def test_resource_index_covers_all_methods_and_existing_owners(self):
        data = json.loads((ROOT / "共享资源" / "规则" / "资源索引.json").read_text(encoding="utf-8"))
        self.assertEqual(len(data["methods"]), 28)
        for group, folder in (("methods", "要素定义库"), ("supplements", "方法补充")):
            for name, owner in data[group].items():
                self.assertTrue((ROOT / "共享资源" / folder / name).is_file(), name)
                self.assertTrue((ROOT / "skills" / owner / "SKILL.md").is_file(), owner)
        for name, owner in data["assets"].items():
            self.assertTrue((ROOT / "共享资源" / name).exists(), name)
            self.assertTrue((ROOT / "skills" / owner / "SKILL.md").is_file(), owner)

    def test_daily_homework_requires_complete_custom_package(self):
        text = (ROOT / "skills" / "dpjf-homework" / "SKILL.md").read_text(encoding="utf-8")
        for required in ("定制文案", "为什么这样写", "拍摄方案", "retrieve_yuliao.py", "语料 ID", "无合适锚点", "完成标准"):
            self.assertIn(required, text)
        self.assertIn("用户已有完整选题、文案或拍法时复用，不重复规划", text)

    def test_unmatched_corpus_record_does_not_win_on_popularity(self):
        module = load_module("retriever", ROOT / "scripts" / "retrieve_yuliao.py")
        fake = {"topics": [], "title": "完全不相干", "opening": "", "copy": "其他", "engagement_value": 999999}
        self.assertEqual(module.score_record(fake, ["不存在的关键词"])[0], 0)
        fake["title"] = "园艺盆栽"
        self.assertGreater(module.score_record(fake, ["盆栽"])[0], 0)

    def test_release_version_has_confirmed_remote_source(self):
        data = json.loads((ROOT / "version.json").read_text(encoding="utf-8"))
        self.assertEqual(data["name"], "dpjf")
        self.assertEqual(data["status"], "released")
        self.assertEqual(data["remote_source"], "https://github.com/sud981953-netizen/dp-jf")

    def test_shared_resources_are_consolidated_and_resolvable(self):
        shared = ROOT / "共享资源"
        self.assertTrue((shared / "规则" / "共同规则.md").is_file())
        self.assertTrue((shared / "要素定义库" / "02_选题要素.md").is_file())
        self.assertTrue((shared / "语料库" / "爆款文案.jsonl").is_file())
        self.assertTrue((shared / "知识卡片库" / "HTML知识卡片" / "logo.png").is_file())
        self.assertFalse((ROOT / "要素定义库").exists())
        self.assertFalse((ROOT / "语料库").exists())
        self.assertTrue((shared / "知识卡片库" / "PNG截图").is_dir())

    def test_retriever_reads_relocated_corpus(self):
        run = subprocess.run([sys.executable, str(ROOT / "scripts" / "retrieve_yuliao.py"), "--id", "126", "--json"], capture_output=True, text=True, encoding="utf-8", check=True)
        self.assertEqual(json.loads(run.stdout)["id"], 126)

    def test_distribution_includes_resources_excludes_private_and_historical(self):
        module = load_module("packager", ROOT / "scripts" / "打包分发包.py")
        files = module.collect_files()
        content = io.BytesIO()
        module.write_archive(content, files)
        with zipfile.ZipFile(content) as archive:
            names = set(archive.namelist())
        self.assertIn("dp-jf/skills/dpjf/SKILL.md", names)
        self.assertIn("dp-jf/skills/dpjf-student/scripts/student_files.py", names)
        self.assertIn("dp-jf/共享资源/00_短视频内容创作72变.md", names)
        self.assertTrue(any("/知识卡片库/PNG截图/" in name for name in names))
        self.assertFalse(any("/_素材资源/" in name or "/历史资料/" in name or "/evals/" in name for name in names))

    def test_distribution_rejects_missing_essential_skill(self):
        module = load_module("packager_missing", ROOT / "scripts" / "打包分发包.py")
        files = [p for p in module.collect_files() if p != ROOT / "skills" / "dpjf-title" / "SKILL.md"]
        with self.assertRaises(ValueError):
            module.write_archive(io.BytesIO(), files)

    def test_manifest_excludes_private_and_historical(self):
        module = load_module("manifest", ROOT / "scripts" / "生成文件清单.py")
        names = [p.relative_to(ROOT).as_posix() for p in module.collect_files(ROOT)]
        self.assertIn("skills/dpjf/SKILL.md", names)
        self.assertFalse(any("_素材资源/" in x or "/历史资料/" in x or x.startswith("evals/") for x in names))


class StudentPathTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module("student_files", ROOT / "skills" / "dpjf-student" / "scripts" / "student_files.py")

    def test_write_and_readback_only_in_student_directory(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "source.md"
            source.write_text("作业", encoding="utf-8")
            target = self.module.write_file(root, "张三", "03_作业与排期", "今天.md", str(source), create=True)
            self.assertEqual(target.read_text(encoding="utf-8"), "作业")
            self.assertIn("张三", target.parts)

    def test_missing_student_and_path_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                self.module.resolve_target(root, "张三", "03_作业与排期", "今天.md")
            (Path(root) / "张三").mkdir()
            with self.assertRaises(ValueError):
                self.module.resolve_target(root, "张三", "03_作业与排期", "../默认.md")

    def test_existing_file_requires_overwrite_permission(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "source.md"
            source.write_text("新", encoding="utf-8")
            target = self.module.write_file(root, "张三", "03_作业与排期", "今天.md", str(source), create=True)
            with self.assertRaises(ValueError):
                self.module.write_file(root, "张三", "03_作业与排期", "今天.md", str(source))
            self.module.write_file(root, "张三", "03_作业与排期", "今天.md", str(source), overwrite=True)
            self.assertEqual(target.read_text(encoding="utf-8"), "新")


if __name__ == "__main__":
    unittest.main()
