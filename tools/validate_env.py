#!/usr/bin/env python3
"""Validate actual deployment values, not just variable names in an example."""
from manage import read_config
if __name__ == "__main__":
    read_config()
    print("Configuration OK")
