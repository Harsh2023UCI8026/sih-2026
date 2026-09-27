import argparse
import dotenv
from dotenv import load_dotenv
load_dotenv()
# duplicate dotenv import removed
import yaml
import os
import sys
import time
from pathlib import Path
from typing import Callable, Any, Dict, Optional

def cache_path(*parts: str) -> Path:
    """Return a Path inside the project's ``cache`` directory.

    ``*parts`` are path components that will be joined under the ``cache``
    directory. The directory hierarchy is created automatically if it does not
    already exist.
    """
    base = Path(__file__).resolve().parents[1] / "cache"
    target = base.joinpath(*parts)
    target.parent.mkdir(parents=True, exist_ok=True)
    return target

def retry(func: Callable[..., Any], *args: Any, max_attempts: int = 3, backoff: int = 2, **kwargs: Any) -> Any:
    """Execute ``func`` with exponential back‑off retry logic.

    The function is called with the supplied ``args`` and ``kwargs``. If it raises
    an exception, it will be retried up to ``max_attempts`` times, waiting
    ``backoff ** attempt`` seconds between attempts.
    """
    attempt = 0
    while True:
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            attempt += 1
            if attempt >= max_attempts:
                raise
            sleep_time = backoff ** attempt
            time.sleep(sleep_time)
            continue

def load_config(preset: str | None = None) -> Dict[str, Any]:
    """Load the project's config.yaml.

    If ``preset`` is provided, return the configuration dictionary for that preset;
    otherwise return the full configuration.
    """
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    with open(config_path, 'r') as f:
        cfg = yaml.safe_load(f) or {}
    if preset:
        presets = cfg.get('presets', {})
        if preset not in presets:
            raise KeyError(f"Preset '{preset}' not defined in config.yaml")
        return presets[preset]
    return cfg

def get_zone_config(parser_description):
    """
    Parses CLI arguments for the target execution zone and enforces safeguards.
    Returns (bbox, preset_name, endpoints_dict).
    bbox format: [min_lon, min_lat, max_lon, max_lat]
    """
    config = load_config()
    
    parser = argparse.ArgumentParser(description=parser_description)
    parser.add_argument('--preset', type=str, default=config.get('default_preset', 'pilot'),
                        help='Named bbox preset (pilot, test_zone, full_delhi)')
    parser.add_argument('--confirm-full-delhi', action='store_true',
                        help='MANDATORY flag to execute the full_delhi preset')
    
    args = parser.parse_args()
    
    preset = args.preset
    if preset not in config['presets']:
        print(f"[ERROR] Preset '{preset}' not found in config.yaml. Available: {list(config['presets'].keys())}")
        sys.exit(1)
        
    if preset == 'full_delhi' and not args.confirm_full_delhi:
        print("[CRITICAL ERROR] You are attempting to run a full city-scale fetch ('full_delhi').")
        print("This will consume massive amounts of API quotas and processing time.")
        print("To proceed, you MUST explicitly pass the --confirm-full-delhi flag.")
        print(f"Example: python {os.path.basename(sys.argv[0])} --preset full_delhi --confirm-full-delhi")
        sys.exit(1)
        
    bbox = config['presets'][preset]['bbox']
    print(f"[INFO] Initializing pipeline for zone: {preset.upper()} - {config['presets'][preset]['description']}")
    print(f"[INFO] Bounding Box (min_lon, min_lat, max_lon, max_lat): {bbox}")
    
    return bbox, preset, config.get('endpoints', {})

if __name__ == "__main__":
    # Test the parsing
    bbox, preset, endpoints = get_zone_config("Test config parser")
