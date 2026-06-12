"""Make src/ importable so tests can import the pipeline modules directly."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))
