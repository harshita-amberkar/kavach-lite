import json
import unittest
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXTENSION_ROOT = PROJECT_ROOT / "extension"
PACKAGE_PATH = (
    PROJECT_ROOT / "static" / "downloads" / "kavach-chrome-extension.zip"
)

# Explicit allowlist: changes to the runtime package layout must update this
# test, so new source files cannot be silently omitted from the download.
RUNTIME_FILES = {
    "manifest.json",
    "detector.js",
    "content.js",
    "options.html",
    "options.js",
}


class ExtensionPackageTests(unittest.TestCase):
    def test_zip_contains_only_current_runtime_files(self):
        with zipfile.ZipFile(PACKAGE_PATH) as package:
            self.assertIsNone(package.testzip(), "ZIP CRC validation failed")
            self.assertEqual(set(package.namelist()), RUNTIME_FILES)

            manifest = json.loads(package.read("manifest.json"))
            referenced_files = {"manifest.json"}
            for content_script in manifest.get("content_scripts", []):
                referenced_files.update(content_script.get("js", []))
                referenced_files.update(content_script.get("css", []))
            options_page = manifest.get("options_ui", {}).get("page")
            if options_page:
                referenced_files.add(options_page)
            background = manifest.get("background", {})
            if background.get("service_worker"):
                referenced_files.add(background["service_worker"])
            action = manifest.get("action", {})
            if action.get("default_popup"):
                referenced_files.add(action["default_popup"])
            for key in ("default_icon",):
                icons = action.get(key, manifest.get(key, {}))
                if isinstance(icons, str):
                    referenced_files.add(icons)
                elif isinstance(icons, dict):
                    referenced_files.update(icons.values())

            self.assertTrue(referenced_files <= RUNTIME_FILES)
            for filename in sorted(RUNTIME_FILES):
                with self.subTest(filename=filename):
                    self.assertEqual(
                        package.read(filename),
                        (EXTENSION_ROOT / filename).read_bytes(),
                    )


if __name__ == "__main__":
    unittest.main()
