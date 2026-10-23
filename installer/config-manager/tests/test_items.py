"""Inline editors for env, exec, binds, monitors, rules and load order."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from support import make_tree
from config_manager import lua_probe, pages, state
from config_manager.rpc import handle


class InlineEditors(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = make_tree(Path(self.tmp.name))
        self._old = state.BACKUP_ROOT
        state.BACKUP_ROOT = Path(self.tmp.name) / "backups"

    def tearDown(self) -> None:
        state.BACKUP_ROOT = self._old
        self.tmp.cleanup()

    def _apply(self, **edit) -> dict:
        res = handle({"id": 1, "method": "apply",
                      "params": {"root": str(self.root), "edits": [edit]}})
        self.assertNotIn("error", res, res)
        return res

    def _item(self, page_id: str, kind: str, nth: int = 0) -> dict:
        data = pages.build(self.root)
        page = next(p for p in data["pages"] if p["id"] == page_id)
        items = [i for i in page["items"] if i["kind"] == kind]
        return items[nth]

    def test_env_value(self) -> None:
        self._apply(type="env", key="XCURSOR_THEME", value="Adwaita")
        self.assertEqual(lua_probe.probe(self.root)["env"]["XCURSOR_THEME"], "Adwaita")

    def test_env_add(self) -> None:
        self._apply(type="env", key="NEW_VAR", value="yes", module="startup.lua")
        self.assertEqual(lua_probe.probe(self.root)["env"]["NEW_VAR"], "yes")

    def test_exec(self) -> None:
        item = self._item("startup", "exec")
        self._apply(type="exec", **{k: item[k] for k in ("file", "line")}, command="hyprpanel")
        commands = [e["command"] for e in lua_probe.probe(self.root)["exec"]]
        self.assertIn("hyprpanel", commands)

    def test_bind_edit(self) -> None:
        item = self._item("startup", "bind")
        self._apply(type="bind", file=item["file"], line=item["line"],
                    keys="SUPER, T", action='hl.dsp.exec_cmd("thunar")')
        bind = lua_probe.probe(self.root)["binds"][0]
        self.assertEqual(bind["keys"], "SUPER, T")
        self.assertEqual(bind["dispatcher"]["__dispatch"], "dsp.exec_cmd")

    def test_bind_add(self) -> None:
        self._apply(type="bind", file="startup.lua", line=0,
                    keys="SUPER, Y", action='hl.dsp.exec_cmd("kitty")')
        keys = [b["keys"] for b in lua_probe.probe(self.root)["binds"]]
        self.assertIn("SUPER, Y", keys)

    def test_monitor_field(self) -> None:
        item = self._item("startup", "monitor")
        self._apply(type="call_field", file=item["file"], line=item["line"],
                    call="monitor", path="scale", value=1.5, valueType="float")
        self.assertAlmostEqual(lua_probe.probe(self.root)["monitors"][0]["scale"], 1.5)

    def test_rule_field(self) -> None:
        item = self._item("startup", "rule")
        self._apply(type="call_field", file=item["file"], line=item["line"],
                    call=item["ruleKind"], path="match.class",
                    value="^(thunar)$", valueType="str")
        rules = lua_probe.probe(self.root)["rules"]["window_rule"]
        self.assertEqual(rules[0]["match"]["class"], "^(thunar)$")

    def test_require_toggle(self) -> None:
        item = next(i for i in self._item_all("hyprland", "require") if i["module"] == "animations-high")
        self._apply(type="require_toggle", line=item["line"],
                    module=item["module"], active=False)
        self.assertNotIn("animations-high", lua_probe.probe(self.root)["requires"])

    def test_require_add(self) -> None:
        self._apply(type="require_add", module="animations-low")
        self.assertIn("animations-low", lua_probe.probe(self.root)["requires"])

    def _item_all(self, page_id: str, kind: str) -> list[dict]:
        data = pages.build(self.root)
        page = next(p for p in data["pages"] if p["id"] == page_id)
        return [i for i in page["items"] if i["kind"] == kind]


if __name__ == "__main__":
    unittest.main()
