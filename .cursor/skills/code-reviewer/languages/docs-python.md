---
language: python
extensions: [".py"]
---

# Python documentation rules

- Flag new public functions/classes in scope without docstrings
- Flag module docstrings missing on CLI entrypoints (`session_cli.py`, `__main__`)
- README must mention `python3`, `pip install -r scripts/requirements.txt` when hub scripts documented
- Flag doctest-style examples that reference removed script names
