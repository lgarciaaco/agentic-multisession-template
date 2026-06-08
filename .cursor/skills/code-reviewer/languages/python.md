---
language: python
extensions: [".py"]
---

# Python rules

Defer style/import nits to `ruff`/`black`/`mypy`/`bandit` when configured.

## Signals

- Flag `print()` in non-CLI paths; unjustified `# noqa` / `# type: ignore`
- Flag `eval`/`exec`, `pickle` on untrusted data, `__import__` with user module names

## Security

- BLOCKER: `subprocess` + `shell=True` + user input; f-string/`%` SQL
- Flag `yaml.load` without `SafeLoader`; prod `DEBUG`/`SECRET_KEY`/`ALLOWED_HOSTS=['*']`
- Flag `render_template_string` + user data; `verify=False` without dev guard

## Types, exceptions, resources

- Flag missing hints on new public APIs; `assert` for external validation; `import *`; mutable defaults
- REQUIRED: bare `except:`; flag `except Exception: pass`, `raise e` vs `raise`, overly broad try blocks
- Flag `open()` without `with`; per-request HTTP sessions; unclosed DB handles; full `.read()` on large files

## Async, perf, idioms

- Flag `time.sleep` in async; blocking I/O or CPU work in `async def` without executor
- Flag `+` concat in loops; `in` on large lists; `re.compile` in loops
- Prefer `pathlib`, `X | None`, guard clauses, `dataclass`/`TypedDict`; flag `is` on non-singleton literals

## Web (`**/api/**`, `**/routes/**`, `**/views/**`, `**/handlers/**`)

- Flag routes without input validation; sync blocking in async handlers; ORM raw/string SQL; missing auth on mutating endpoints
