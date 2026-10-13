#!/usr/bin/env python3
"""VENOM4 Pro safe entry point.

The historical implementation in this repository contained unsafe routines.
The entry point now launches the modular, offline-first BGXTEAM Security Desk.
"""
from bgxdesk.main import main


if __name__ == "__main__":
    main()
