"""Load the plugin's user configuration.

The config lives outside the plugin directory (~/.claude/research-system-config/) so
it survives plugin updates. Both automation scripts and the utilities import this one
loader; do not copy it into another script.
"""

from pathlib import Path

import yaml

CONFIG_PATH = Path.home() / ".claude" / "research-system-config" / "config.yaml"


def load_config(config_path=CONFIG_PATH):
    """Return the parsed config.yaml after checking that research_root exists."""
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(
            f"Config file not found at {config_path}\n"
            f"Please create ~/.claude/research-system-config/config.yaml\n"
            f"See the plugin's config/config.template.yaml for reference."
        )

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    research_root = Path(config["paths"]["research_root"]).expanduser().resolve()
    if not research_root.exists():
        raise ValueError(f"research_root does not exist: {research_root}\nPlease check your config.yaml file.")
    if not research_root.is_dir():
        raise ValueError(f"research_root is not a directory: {research_root}\nPlease check your config.yaml file.")

    return config


def data_dir(config):
    """The tracking directory ({research_root}/{paths.data}) as a Path."""
    research_root = Path(config["paths"]["research_root"]).expanduser().resolve()
    return research_root / config["paths"]["data"]
