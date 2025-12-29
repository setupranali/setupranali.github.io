"""
SetuPranali CLI - Command-line interface for managing SetuPranali

Usage:
    setupranali --help
    setupranali health
    setupranali datasets list
    setupranali query orders -d city -m revenue
"""

from .setupranali_cli import cli, main

__version__ = "1.1.0"
__all__ = ["cli", "main"]

