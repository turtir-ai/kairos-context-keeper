#!/usr/bin/env python3
"""
Version bump script for Kairos
Automatically increments the version number in config
"""

import toml
from pathlib import Path

CONFIG_PATH = Path("../kairos.toml")

if __name__ == "__main__":
    print("🔄 Bumping version...")
    
    # Load the existing config
    with open(CONFIG_PATH, "r") as f:
        config = toml.load(f)
        
    # Extract and parse version
    version = config.get("general", {}).get("version", "0.0.0")
    major, minor, patch = map(int, version.split('.'))
    
    # Increment patch version
    patch += 1
    new_version = f"{major}.{minor}.{patch}"
    
    # Update config
    config["general"]["version"] = new_version
    
    with open(CONFIG_PATH, "w") as f:
        toml.dump(config, f)
        
    print(f"✅ Version updated to {new_version} in {CONFIG_PATH}")

