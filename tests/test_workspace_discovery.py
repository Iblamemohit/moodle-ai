import os
import json
import unittest
import asyncio
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

from src.config import (
    get_workspace_dir,
    set_active_workspace,
    reset_active_workspace,
    discover_available_workspaces,
    get_config,
    save_env_config
)
import src.config as cfg_module
from src.mcp_server import mcp


class TestWorkspaceDiscovery(unittest.TestCase):
    def setUp(self):
        reset_active_workspace()
        self.orig_env = os.environ.get("MOODLE_AI_ROOT")
        if "MOODLE_AI_ROOT" in os.environ:
            del os.environ["MOODLE_AI_ROOT"]

    def tearDown(self):
        reset_active_workspace()
        if self.orig_env is not None:
            os.environ["MOODLE_AI_ROOT"] = self.orig_env
        elif "MOODLE_AI_ROOT" in os.environ:
            del os.environ["MOODLE_AI_ROOT"]

    def test_01_default_workspace_resolution(self):
        """Default workspace resolves to the active project root."""
        ws = get_workspace_dir()
        self.assertTrue(ws.exists())
        self.assertTrue((ws / "moodle.py").exists())
        self.assertEqual(ws.resolve(), PROJECT_ROOT.resolve())

    def test_02_env_var_override(self):
        """MOODLE_AI_ROOT environment variable redirects workspace and all child paths."""
        custom_dir = PROJECT_ROOT
        os.environ["MOODLE_AI_ROOT"] = str(custom_dir)
        ws = get_workspace_dir()
        self.assertEqual(ws, custom_dir.resolve())

        conf = get_config()
        self.assertEqual(conf["workspace_dir"], str(custom_dir.resolve()))
        self.assertEqual(conf["db_path"], str((custom_dir / "data/moodle_knowledge.db").resolve()))
        self.assertEqual(conf["output_dir"], str((custom_dir / "output").resolve()))

    def test_03_programmatic_runtime_switch(self):
        """set_active_workspace dynamically changes workspace and clears cache."""
        target = PROJECT_ROOT
        set_active_workspace(target)
        self.assertEqual(get_workspace_dir(), target.resolve())

        conf = get_config()
        self.assertEqual(conf["workspace_dir"], str(target.resolve()))

        # Non-existent workspace raises FileNotFoundError
        with self.assertRaises(FileNotFoundError):
            set_active_workspace("/non/existent/path/for/sure_123")

    def test_04_discover_available_workspaces(self):
        """discover_available_workspaces returns structured metadata for available environments."""
        workspaces = discover_available_workspaces()
        self.assertIsInstance(workspaces, list)
        self.assertGreater(len(workspaces), 0)
        found_paths = [w["path"] for w in workspaces]
        self.assertIn(str(PROJECT_ROOT.resolve()), found_paths)
        for w in workspaces:
            self.assertIn("label", w)
            self.assertIn("path", w)
            self.assertIn("type", w)
            self.assertIn("has_database", w)

    def test_05_dynamic_module_attributes(self):
        """Module attributes WORKSPACE_DIR and ENV_PATH resolve dynamically via __getattr__."""
        self.assertEqual(cfg_module.WORKSPACE_DIR, PROJECT_ROOT.resolve())
        self.assertEqual(cfg_module.ENV_PATH, (PROJECT_ROOT / ".env").resolve())

    def test_06_mcp_workspace_tools(self):
        """MCP tools get_workspace_info and switch_active_workspace function properly."""
        tools = mcp._tool_manager._tools
        self.assertIn("get_workspace_info", tools)
        self.assertIn("switch_active_workspace", tools)

        # Call get_workspace_info via MCP tool manager
        async def run_get_info():
            return await mcp._tool_manager.call_tool("get_workspace_info", {}, None, convert_result=False)

        res_info_json = asyncio.run(run_get_info())
        info = json.loads(res_info_json)
        self.assertEqual(info["status"], "success")
        self.assertEqual(info["active_workspace"], str(PROJECT_ROOT.resolve()))
        self.assertIn("discovered_workspaces", info)

        # Call switch_active_workspace via MCP tool manager
        async def run_switch():
            return await mcp._tool_manager.call_tool(
                "switch_active_workspace",
                {"workspace_path": str(PROJECT_ROOT)},
                None,
                convert_result=False
            )

        res_switch_json = asyncio.run(run_switch())
        switch_res = json.loads(res_switch_json)
        self.assertEqual(switch_res["status"], "success")


if __name__ == "__main__":
    unittest.main()
