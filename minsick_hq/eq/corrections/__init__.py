"""Measured corrections for specific headsets, from the AutoEQ project (MIT licence; credited in
NOTICE.md). Each .txt here is AutoEQ's ParametricEQ.txt exactly as published, with a few header
lines saying what it is: name, a note for the person, and where it came from.
"""
import os

from .. import autoeq

HERE = os.path.dirname(os.path.abspath(__file__))
# The ones measured with fewer extremes first
ORDER = ["maxwell_kuulokenurkka.txt", "maxwell_rtings.txt"]


def _header(text):
    fields = {}
    for line in text.splitlines():
        if line.startswith("# ") and ":" in line:
            key, _, value = line[2:].partition(":")
            fields[key.strip()] = value.strip()
    return fields


def load():
    """[{"name", "note", "source", "preamp", "bands"}] for every correction file."""
    files = sorted(f for f in os.listdir(HERE) if f.endswith(".txt"))
    files.sort(key=lambda f: ORDER.index(f) if f in ORDER else len(ORDER))
    entries = []
    for name in files:
        with open(os.path.join(HERE, name)) as file:
            text = file.read()
        fields = _header(text)
        entries.append({"name": fields.get("name", name[:-4]), "note": fields.get("note", ""),
                        "source": fields.get("source", ""), **autoeq.parse(text)})
    return entries
