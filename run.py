"""Launcher used by PyInstaller and by 'Start with Windows' in dev mode."""
import sys

from pomodoro.main import main

if __name__ == "__main__":
    sys.exit(main())
