"""
Veritas Core Plugin Manager

Handles discovery, loading, and lifecycle of plugins.
Plugins are discovered from the configured plugin directory (default: /opt/veritas/plugins).

Each plugin must have a manifest.json file with metadata and a routes module
that exports a FastAPI router.

Example manifest.json:
    {
        "name": "scholarly-hollows",
        "version": "1.0.0",
        "display_name": "Scholarly Hollows",
        "description": "Academic magic spells for Veritas",
        "requires_veritas_version": ">=1.0.0",
        "api_prefix": "/api/v1/sh",
        "routes_module": "routes"
    }
"""

import importlib.util
import json
import logging
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI

logger = logging.getLogger(__name__)


class PluginManager:
    """Veritas Core 插件管理器"""

    def __init__(self, plugin_dir: str = "/opt/veritas/plugins"):
        """
        Initialize the plugin manager.

        Args:
            plugin_dir: Directory containing installed plugins
        """
        self.plugin_dir = Path(plugin_dir)
        self.loaded_plugins: List[str] = []

    def discover(self) -> List[dict]:
        """
        发现已安装插件

        Scans the plugin directory for subdirectories containing manifest.json files.
        Returns a list of manifest dictionaries with the plugin path added.

        Returns:
            List of plugin manifests with 'path' field added
        """
        plugins = []

        if not self.plugin_dir.exists():
            logger.warning(f"Plugin directory does not exist: {self.plugin_dir}")
            return plugins

        for path in self.plugin_dir.iterdir():
            if not path.is_dir():
                continue

            manifest_path = path / "manifest.json"
            if manifest_path.exists():
                try:
                    with open(manifest_path, encoding="utf-8") as f:
                        manifest = json.load(f)
                        manifest["path"] = str(path)
                        plugins.append(manifest)
                        logger.debug(f"Discovered plugin: {manifest.get('name', 'unknown')}")
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid manifest.json in {path}: {e}")
                except Exception as e:
                    logger.error(f"Error reading manifest from {path}: {e}")

        logger.info(f"Discovered {len(plugins)} plugin(s)")
        return plugins

    def load(self, app: FastAPI, plugin_name: str) -> bool:
        """
        加载插件路由到 FastAPI

        Dynamically imports the plugin's routes module and registers
        the router with the FastAPI app.

        Args:
            app: The FastAPI application instance
            plugin_name: Name of the plugin to load (directory name)

        Returns:
            True if plugin loaded successfully, False otherwise
        """
        try:
            plugin_path = self.plugin_dir / plugin_name
            manifest_path = plugin_path / "manifest.json"

            if not manifest_path.exists():
                logger.error(f"Manifest not found for plugin: {plugin_name}")
                return False

            with open(manifest_path, encoding="utf-8") as f:
                manifest = json.load(f)

            routes_module_name = manifest.get("routes_module", "routes")
            routes_init_path = plugin_path / routes_module_name / "__init__.py"

            if not routes_init_path.exists():
                logger.error(f"Routes module not found: {routes_init_path}")
                return False

            # 动态导入路由模块
            spec = importlib.util.spec_from_file_location(
                f"plugins.{plugin_name}.{routes_module_name}",
                routes_init_path
            )

            if spec is None or spec.loader is None:
                logger.error(f"Failed to create module spec for {plugin_name}")
                return False

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # 注册路由
            if hasattr(module, "router"):
                api_prefix = manifest.get("api_prefix", f"/api/v1/plugins/{plugin_name}")
                display_name = manifest.get("display_name", plugin_name)

                app.include_router(
                    module.router,
                    prefix=api_prefix,
                    tags=[display_name]
                )

                self.loaded_plugins.append(plugin_name)
                logger.info(f"Loaded plugin: {plugin_name} at {api_prefix}")
                return True
            else:
                logger.warning(f"Plugin {plugin_name} has no 'router' export")
                return False

        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_name}: {e}")
            return False

    def load_all(self, app: FastAPI) -> int:
        """
        加载所有发现的插件

        Discovers all plugins and attempts to load each one.

        Args:
            app: The FastAPI application instance

        Returns:
            Number of successfully loaded plugins
        """
        loaded_count = 0
        for plugin in self.discover():
            plugin_name = plugin.get("name")
            if plugin_name and self.load(app, plugin_name):
                loaded_count += 1

        logger.info(f"Loaded {loaded_count} plugin(s)")
        return loaded_count

    def get_plugin_info(self, plugin_name: str) -> Optional[dict]:
        """
        Get manifest info for a specific plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Plugin manifest dict or None if not found
        """
        manifest_path = self.plugin_dir / plugin_name / "manifest.json"

        if not manifest_path.exists():
            return None

        try:
            with open(manifest_path, encoding="utf-8") as f:
                manifest = json.load(f)
                manifest["path"] = str(self.plugin_dir / plugin_name)
                manifest["loaded"] = plugin_name in self.loaded_plugins
                return manifest
        except Exception:
            return None

    def is_loaded(self, plugin_name: str) -> bool:
        """Check if a plugin is currently loaded."""
        return plugin_name in self.loaded_plugins
