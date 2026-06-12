#!/usr/bin/env python3
"""Compare and apply in-place upgrades from the agentic-multisession-template upstream."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from hub_git import _validate_branch
from repos import workspace_root

DEFAULT_UPSTREAM = "https://github.com/lgarciaaco/agentic-multisession-template.git"
DEFAULT_UPSTREAM_HOST = "github.com"
DEFAULT_UPSTREAM_REPO_SUFFIX = "agentic-multisession-template"
DEFAULT_UPSTREAM_REF = "main"
HUB_VERSION_FILE = ".hub-version"
HUB_UPSTREAM_FILE = ".hub-upstream"
UPSTREAM_CACHE_DIR = ".hub-upstream-cache"
UPGRADE_STAGING_DIR = ".hub-upgrade-staging"
_GIT_TIMEOUT_SEC = 300

_VERSION_RE = re.compile(r"^## \[([0-9]+\.[0-9]+\.[0-9]+(?:-[a-zA-Z0-9][a-zA-Z0-9.]*)?)\]\s*(?:-\s*(\d{4}-\d{2}-\d{2}))?")
_IMPACT_RE = re.compile(r"\*\*Impact:\*\*\s*(none|optional|required)\b", re.IGNORECASE)
_SECTION_RE = re.compile(r"^### (.+)$")
_SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9][a-zA-Z0-9.]*)?$")

HUB_MANAGED_PATHS: tuple[str, ...] = (
    "scripts",
    ".cursor",
    "docs",
    "sessions/_template",
    "sessions/_codenames.example.yaml",
    "sessions/index.example.json",
    "sessions/_inbox/README.md",
    "repos/.gitkeep",
    "AGENTS.md",
    "SESSIONS.md",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    "CUSTOMIZE.md",
    "README.md",
    "repos.yaml.example",
    "LICENSE",
    HUB_VERSION_FILE,
    ".hub-upstream.example",
)

POST_UPGRADE_STEPS = (
    "pip install -r scripts/requirements.txt",
    "./scripts/install-workspace-agent.sh",
    "python3 scripts/test_session_binding.py",
    "python3 scripts/test_hub_upgrade.py",
)


@dataclass
class Release:
    version: str
    date: str | None = None
    hub_bullets: list[str] = field(default_factory=list)
    session_impact: str = "optional"
    session_notes: list[str] = field(default_factory=list)


@dataclass
class UpstreamSnapshot:
    tree: Path
    url: str
    ref: str
    sha: str


def parse_version(value: str) -> tuple:
    stripped = value.strip().lstrip("v")
    core, *pre_parts = stripped.split("-", 1)
    pre = pre_parts[0] if pre_parts else None
    parts = core.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise ValueError(f"invalid semver: {value!r}")
    numeric = tuple(int(p) for p in parts)
    pre_key: tuple = (1,) if pre is None else (0, pre)
    return numeric + pre_key


def validate_semver(value: str) -> str:
    name = value.strip().lstrip("v")
    if not _SEMVER_RE.fullmatch(name):
        raise ValueError(f"invalid semver: {value!r}")
    return name


def compare_versions(left: str, right: str) -> int:
    a = parse_version(left)
    b = parse_version(right)
    if a < b:
        return -1
    if a > b:
        return 1
    return 0


def read_installed_version(root: Path | None = None) -> str | None:
    root = root or workspace_root()
    path = root / HUB_VERSION_FILE
    if not path.exists():
        return None
    value = path.read_text().strip()
    return value or None


def parse_changelog(text: str) -> list[Release]:
    releases: list[Release] = []
    current: Release | None = None
    current_section: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        heading = _VERSION_RE.match(line)
        if heading:
            if current:
                releases.append(current)
            current = Release(version=heading.group(1), date=heading.group(2))
            current_section = None
            continue
        if current is None:
            continue

        section_match = _SECTION_RE.match(line)
        if section_match:
            current_section = section_match.group(1).strip().lower()
            continue

        if current_section == "session notes":
            impact = _IMPACT_RE.search(line)
            if impact:
                current.session_impact = impact.group(1).lower()
                continue
            bullet = line.strip()
            if bullet.startswith("- "):
                current.session_notes.append(bullet[2:].strip())
            continue

        if current_section in {"added", "changed", "fixed", "hub changes"}:
            bullet = line.strip()
            if bullet.startswith("- "):
                current.hub_bullets.append(bullet[2:].strip())

    if current:
        releases.append(current)
    return releases


def read_version_from_tree(root: Path) -> str | None:
    path = root / HUB_VERSION_FILE
    if path.exists():
        value = path.read_text().strip()
        if value:
            return validate_semver(value)
    changelog = root / "CHANGELOG.md"
    if not changelog.exists():
        return None
    releases = parse_changelog(changelog.read_text())
    if not releases:
        return None
    return max(releases, key=lambda item: parse_version(item.version)).version


def releases_between(
    releases: list[Release], current: str | None, latest: str
) -> list[Release]:
    if current is None:
        pending = [
            release
            for release in releases
            if compare_versions(release.version, latest) <= 0
        ]
    else:
        pending = []
        for release in releases:
            if compare_versions(release.version, current) <= 0:
                continue
            if compare_versions(release.version, latest) <= 0:
                pending.append(release)
    pending.sort(key=lambda item: parse_version(item.version))
    return pending


def _read_upstream_file(root: Path) -> str | None:
    path = root / HUB_UPSTREAM_FILE
    if not path.exists():
        return None
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return stripped
    return None


def resolve_upstream_url(root: Path | None = None) -> str:
    env = os.environ.get("WORKSPACE_TEMPLATE_UPSTREAM", "").strip()
    if env:
        return env

    root = root or workspace_root()
    local = _read_upstream_file(root)
    if local:
        return local

    return DEFAULT_UPSTREAM


def _upstream_is_trusted(url: str) -> bool:
    if url.rstrip("/") == DEFAULT_UPSTREAM.rstrip("/"):
        return True
    parsed = urlparse(url)
    if parsed.scheme != "https":
        return False
    host = (parsed.hostname or "").lower()
    if host != DEFAULT_UPSTREAM_HOST:
        return False
    path = (parsed.path or "").rstrip("/")
    return path.endswith(f"/{DEFAULT_UPSTREAM_REPO_SUFFIX}") or path.endswith(
        DEFAULT_UPSTREAM_REPO_SUFFIX
    )


def validate_upstream_url(url: str, *, allow_untrusted: bool = False) -> str:
    cleaned = url.strip()
    if not cleaned:
        raise ValueError("upstream URL is empty")
    parsed = urlparse(cleaned)
    if parsed.scheme not in {"https", "http"}:
        raise ValueError(f"unsupported upstream scheme: {parsed.scheme!r}")
    if parsed.scheme == "http":
        raise ValueError("upstream URL must use https")
    if not parsed.netloc:
        raise ValueError(f"invalid upstream URL: {cleaned!r}")
    if not allow_untrusted and not _upstream_is_trusted(cleaned):
        raise ValueError(
            "upstream URL is not the default template repo; set WORKSPACE_ALLOW_UNTRUSTED_UPSTREAM=1 "
            "or pass --allow-untrusted-upstream to hub-upgrade.sh"
        )
    return cleaned


def upstream_ref() -> str:
    raw = os.environ.get("WORKSPACE_TEMPLATE_REF", DEFAULT_UPSTREAM_REF).strip() or DEFAULT_UPSTREAM_REF
    return _validate_branch(raw)


def version_ref(version: str) -> str:
    return f"v{validate_semver(version)}"


def _run_git(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        check=check,
        timeout=_GIT_TIMEOUT_SEC,
    )


def _git_short_sha(repo: Path) -> str:
    return _run_git(["git", "-C", str(repo), "rev-parse", "--short", "HEAD"]).stdout.strip()


def ensure_upstream_tree(
    root: Path,
    url: str,
    ref: str,
    *,
    allow_untrusted: bool = False,
    fetch: bool = True,
) -> UpstreamSnapshot:
    url = validate_upstream_url(url, allow_untrusted=allow_untrusted)
    ref = _validate_branch(ref)
    cache = root / UPSTREAM_CACHE_DIR

    if fetch or not (cache / ".git").exists():
        if not (cache / ".git").exists():
            cache.parent.mkdir(parents=True, exist_ok=True)
            if cache.exists():
                resolved = cache.resolve()
                root_resolved = root.resolve()
                try:
                    resolved.relative_to(root_resolved)
                except ValueError as exc:
                    raise RuntimeError(
                        f"refusing to remove cache outside hub root: {cache}"
                    ) from exc
                if cache.is_symlink():
                    raise RuntimeError(f"refusing to remove symlink cache: {cache}")
                shutil.rmtree(cache)
            result = _run_git(
                ["git", "clone", "--depth", "1", "--branch", ref, "--", url, str(cache)],
                check=False,
            )
            if result.returncode != 0:
                msg = result.stderr.strip() or result.stdout.strip() or "git clone failed"
                raise RuntimeError(f"could not clone upstream template ({url}@{ref}): {msg}")
        else:
            fetch_result = _run_git(
                ["git", "-C", str(cache), "fetch", "origin", "--depth", "1", "--prune", ref],
                check=False,
            )
            if fetch_result.returncode != 0:
                msg = fetch_result.stderr.strip() or fetch_result.stdout.strip() or "git fetch failed"
                raise RuntimeError(f"could not fetch upstream template ({url}@{ref}): {msg}")
            checkout = _run_git(
                ["git", "-C", str(cache), "checkout", "--force", "FETCH_HEAD"],
                check=False,
            )
            if checkout.returncode != 0:
                msg = checkout.stderr.strip() or checkout.stdout.strip() or "git checkout failed"
                raise RuntimeError(f"could not checkout upstream template ref ({ref}): {msg}")
    elif not (cache / ".git").exists():
        raise RuntimeError(
            "upstream cache missing; run ./scripts/hub-status.sh without --cached-only first"
        )

    return UpstreamSnapshot(
        tree=cache,
        url=url,
        ref=ref,
        sha=_git_short_sha(cache),
    )


def _read_upstream_releases(tree: Path) -> list[Release]:
    changelog = tree / "CHANGELOG.md"
    if not changelog.exists():
        raise FileNotFoundError(f"missing upstream CHANGELOG.md in {tree}")
    return parse_changelog(changelog.read_text())


def _plain_summary(releases: list[Release]) -> str:
    if not releases:
        return "You are already on the latest hub template version."
    chunks: list[str] = []
    for release in releases:
        headline = release.hub_bullets[:3]
        if headline:
            chunks.append(f"{release.version}: " + "; ".join(headline))
        else:
            chunks.append(f"{release.version}: hub machinery updates")
    return " ".join(chunks)


def _session_guidance(releases: list[Release]) -> dict:
    required = [release for release in releases if release.session_impact == "required"]
    optional = [release for release in releases if release.session_impact == "optional"]
    none = [release for release in releases if release.session_impact == "none"]
    notes: list[str] = []
    for release in releases:
        notes.extend(release.session_notes)
    impact = "none"
    if required:
        impact = "required"
    elif optional:
        impact = "optional"
    elif none and len(none) == len(releases):
        impact = "none"
    return {
        "impact": impact,
        "required_versions": [release.version for release in required],
        "optional_versions": [release.version for release in optional],
        "notes": notes,
    }


def _allow_untrusted_upstream() -> bool:
    return os.environ.get("WORKSPACE_ALLOW_UNTRUSTED_UPSTREAM", "").strip() in {
        "1",
        "true",
        "yes",
    }


def hub_status(root: Path | None = None, *, fetch: bool = True) -> dict:
    root = root or workspace_root()
    current = read_installed_version(root)
    upstream = resolve_upstream_url(root)
    allow_untrusted = _allow_untrusted_upstream()

    try:
        ref = upstream_ref()
        snapshot = ensure_upstream_tree(
            root,
            upstream,
            ref,
            allow_untrusted=allow_untrusted,
            fetch=fetch,
        )
    except (RuntimeError, ValueError) as exc:
        raw_ref = (
            os.environ.get("WORKSPACE_TEMPLATE_REF", DEFAULT_UPSTREAM_REF).strip()
            or DEFAULT_UPSTREAM_REF
        )
        return {
            "state": "upstream_unreachable",
            "current_version": current,
            "latest_version": None,
            "update_available": False,
            "upstream": upstream,
            "upstream_ref": raw_ref,
            "error": str(exc),
            "agent_action": (
                "Could not reach the template upstream. Check network, WORKSPACE_TEMPLATE_UPSTREAM, "
                "or .hub-upstream, then retry ./scripts/hub-status.sh."
            ),
        }

    try:
        latest = read_version_from_tree(snapshot.tree)
        upstream_releases = _read_upstream_releases(snapshot.tree)
    except (FileNotFoundError, ValueError) as exc:
        return {
            "state": "upstream_invalid",
            "current_version": current,
            "latest_version": None,
            "update_available": False,
            "upstream": upstream,
            "upstream_ref": ref,
            "upstream_sha": snapshot.sha,
            "error": str(exc),
            "agent_action": "Report upstream parse failure; do not upgrade.",
        }

    pending = releases_between(upstream_releases, current, latest)
    update_available = current is None or compare_versions(current, latest) < 0
    guidance = _session_guidance(pending)

    return {
        "state": "ok",
        "current_version": current,
        "latest_version": latest,
        "update_available": update_available,
        "upstream": upstream,
        "upstream_ref": ref,
        "upstream_sha": snapshot.sha,
        "upstream_trusted": _upstream_is_trusted(upstream),
        "pending_releases": [
            {
                "version": release.version,
                "date": release.date,
                "hub_summary": release.hub_bullets,
                "session_impact": release.session_impact,
                "session_notes": release.session_notes,
            }
            for release in pending
        ],
        "plain_summary": _plain_summary(pending),
        "session_guidance": guidance,
        "post_upgrade_steps": list(POST_UPGRADE_STEPS),
        "agent_action": (
            "Explain current vs latest in plain language. If the user says upgrade, load "
            "`.cursor/skills/hub-upgrade/SKILL.md` and run `./scripts/hub-upgrade.sh --yes`."
        ),
    }


def _path_within_root(root: Path, target: Path) -> Path:
    resolved = target.resolve()
    root_resolved = root.resolve()
    if resolved != root_resolved:
        resolved.relative_to(root_resolved)
    return resolved


def _copy_managed_path(src_root: Path, dst_root: Path, rel: str) -> None:
    src = _path_within_root(src_root, src_root / rel)
    dst = _path_within_root(dst_root, dst_root / rel)
    if dst.exists() and dst.is_symlink():
        raise RuntimeError(f"refusing to replace symlink destination: {dst}")
    if not src.exists():
        return
    if src.is_dir():
        if dst.exists():
            if dst.is_symlink():
                raise RuntimeError(f"refusing to replace symlink destination: {dst}")
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _stage_managed_paths(
    src_root: Path, staging_root: Path, rel_paths: list[str]
) -> list[str]:
    copied: list[str] = []
    for rel in rel_paths:
        src = src_root / rel
        if not src.exists():
            continue
        _copy_managed_path(src_root, staging_root, rel)
        copied.append(rel)
    return copied


def _apply_staged_paths(staging_root: Path, dst_root: Path, rel_paths: list[str]) -> None:
    for rel in rel_paths:
        _copy_managed_path(staging_root, dst_root, rel)


def _resolve_upgrade_snapshot(
    root: Path,
    upstream: str,
    target: str,
    *,
    allow_untrusted: bool,
) -> UpstreamSnapshot:
    tag_ref = version_ref(target)
    try:
        return ensure_upstream_tree(
            root,
            upstream,
            tag_ref,
            allow_untrusted=allow_untrusted,
            fetch=True,
        )
    except RuntimeError:
        latest_ref = upstream_ref()
        snapshot = ensure_upstream_tree(
            root,
            upstream,
            latest_ref,
            allow_untrusted=allow_untrusted,
            fetch=True,
        )
        tree_version = read_version_from_tree(snapshot.tree)
        if tree_version != target:
            raise RuntimeError(
                f"upstream tag {tag_ref} not found and {latest_ref} resolves to {tree_version}, "
                f"not requested {target}"
            ) from None
        return snapshot


def hub_upgrade(
    root: Path | None = None,
    *,
    target_version: str | None = None,
    dry_run: bool = False,
) -> dict:
    root = root or workspace_root()
    allow_untrusted = _allow_untrusted_upstream()
    status = hub_status(root, fetch=True)
    if status.get("state") != "ok":
        return {"ok": False, "dry_run": dry_run, **status}

    current = status["current_version"]
    latest = status["latest_version"]
    if latest is None:
        return {
            "ok": False,
            "dry_run": dry_run,
            "error": "upstream latest version missing after status check",
            "current_version": current,
        }

    target = target_version or latest
    try:
        target = validate_semver(target)
    except ValueError as exc:
        return {
            "ok": False,
            "dry_run": dry_run,
            "error": str(exc),
            "current_version": current,
            "latest_version": latest,
        }

    if compare_versions(target, latest) > 0:
        return {
            "ok": False,
            "dry_run": dry_run,
            "error": f"target version {target} is newer than upstream latest {latest}",
            "current_version": current,
            "latest_version": latest,
        }
    if current and compare_versions(current, target) >= 0:
        return {
            "ok": True,
            "dry_run": dry_run,
            "changed": False,
            "message": f"Already at {current}; nothing to upgrade.",
            "current_version": current,
            "latest_version": latest,
            "target_version": target,
        }

    upstream = status["upstream"]
    try:
        snapshot = _resolve_upgrade_snapshot(
            root,
            upstream,
            target,
            allow_untrusted=allow_untrusted,
        )
    except (RuntimeError, ValueError) as exc:
        return {
            "ok": False,
            "dry_run": dry_run,
            "error": str(exc),
            "current_version": current,
            "latest_version": latest,
            "target_version": target,
            "upstream": upstream,
        }

    tree_version = read_version_from_tree(snapshot.tree)
    if tree_version != target:
        return {
            "ok": False,
            "dry_run": dry_run,
            "error": (
                f"upstream tree version {tree_version} does not match requested target {target}"
            ),
            "current_version": current,
            "latest_version": latest,
            "target_version": target,
            "upstream": upstream,
            "upstream_ref": snapshot.ref,
            "upstream_sha": snapshot.sha,
        }

    rel_paths = list(HUB_MANAGED_PATHS)
    copied = [rel for rel in rel_paths if (snapshot.tree / rel).exists()]
    if not copied:
        return {
            "ok": False,
            "dry_run": dry_run,
            "error": "upstream template has no hub-managed paths to copy",
            "current_version": current,
            "latest_version": latest,
            "target_version": target,
            "upstream": upstream,
            "upstream_ref": snapshot.ref,
            "upstream_sha": snapshot.sha,
        }

    if dry_run:
        upstream_releases = _read_upstream_releases(snapshot.tree)
        pending = releases_between(upstream_releases, current, target)
        return {
            "ok": True,
            "dry_run": True,
            "changed": True,
            "current_version": current,
            "target_version": target,
            "latest_version": latest,
            "copied_paths": copied,
            "pending_releases": [release.version for release in pending],
            "session_guidance": _session_guidance(pending),
            "post_upgrade_steps": list(POST_UPGRADE_STEPS),
            "upstream": upstream,
            "upstream_ref": snapshot.ref,
            "upstream_sha": snapshot.sha,
            "message": f"Would upgrade hub layer to {target}.",
        }

    staging_parent = root / UPGRADE_STAGING_DIR
    if staging_parent.exists():
        if staging_parent.is_symlink():
            raise RuntimeError(f"refusing to use symlink staging dir: {staging_parent}")
        shutil.rmtree(staging_parent)
    staging_parent.mkdir(parents=True, exist_ok=True)
    staging_dir = Path(
        tempfile.mkdtemp(prefix="hub-upgrade-", dir=str(staging_parent))
    )

    try:
        staged = _stage_managed_paths(snapshot.tree, staging_dir, copied)
        if len(staged) != len(copied):
            raise RuntimeError("staging failed for one or more hub-managed paths")
        _apply_staged_paths(staging_dir, root, staged)
        (root / HUB_VERSION_FILE).write_text(f"{target}\n")
    except Exception:
        shutil.rmtree(staging_dir, ignore_errors=True)
        raise
    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)
        if staging_parent.exists() and not any(staging_parent.iterdir()):
            staging_parent.rmdir()

    upstream_releases = _read_upstream_releases(snapshot.tree)
    pending = releases_between(upstream_releases, current, target)
    return {
        "ok": True,
        "dry_run": False,
        "changed": True,
        "current_version": current,
        "target_version": target,
        "latest_version": latest,
        "copied_paths": copied,
        "pending_releases": [release.version for release in pending],
        "session_guidance": _session_guidance(pending),
        "post_upgrade_steps": list(POST_UPGRADE_STEPS),
        "upstream": upstream,
        "upstream_ref": snapshot.ref,
        "upstream_sha": snapshot.sha,
        "message": f"Upgraded hub layer to {target}.",
    }
