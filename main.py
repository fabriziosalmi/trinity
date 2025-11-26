#!/usr/bin/env python3
"""
Trinity Core - Main Entry Point (Legacy Wrapper)

DEPRECATED: This file is maintained for backward compatibility only.
Use the modern CLI instead:
    poetry run trinity build --theme brutalist --guardian

This wrapper delegates all functionality to src/trinity/cli.py
No more sys.path hacking, no code duplication.
"""

if __name__ == "__main__":
    # FIXED: No more sys.path manipulation (Rule #13, #18)
    # FIXED: No code duplication - delegate to CLI (DRY principle)
    from trinity.cli import app
    
    print("⚠️  Warning: main.py is deprecated.")
    print("   Use: poetry run trinity <command> instead")
    print()
    
    # Run CLI app
    app()
