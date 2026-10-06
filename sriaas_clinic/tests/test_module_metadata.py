import json
from pathlib import Path
from unittest import TestCase

from sriaas_clinic import hooks
from sriaas_clinic.setup.utils import MODULE_DEF_NAME
from sriaas_clinic.uninstall import MODULE as UNINSTALL_MODULE


class TestModuleMetadata(TestCase):
    def test_module_references_use_canonical_name(self):
        package_root = Path(__file__).resolve().parents[1]
        canonical_name = (package_root / "modules.txt").read_text(encoding="utf-8").strip()

        self.assertEqual(canonical_name, "Sriaas Clinic")
        self.assertEqual(MODULE_DEF_NAME, canonical_name)
        self.assertEqual(UNINSTALL_MODULE, canonical_name)

        for fixture in hooks.fixtures:
            for fieldname, operator, value in fixture.get("filters", []):
                if fieldname == "module" and operator == "=":
                    self.assertEqual(value, canonical_name)

        shipkia_settings = json.loads(
            (
                package_root
                / "sriaas_clinic"
                / "doctype"
                / "shipkia_settings"
                / "shipkia_settings.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(shipkia_settings["module"], canonical_name)
