"""Audit a viva-* repo for compliance with the bigraph-schema discovery convention."""
from __future__ import annotations
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomllib  # type: ignore[no-redef]
    except ImportError:
        import tomli as tomllib  # type: ignore[no-redef]


@dataclass
class CheckResult:
    name: str
    status: str  # "PASS", "WARN", "FAIL"
    detail: str = ""


@dataclass
class AuditReport:
    target: str  # path or repo name
    checks: list[CheckResult] = field(default_factory=list)
    fixes: list[str] = field(default_factory=list)

    def add(self, name: str, status: str, detail: str = "", fix: str = ""):
        self.checks.append(CheckResult(name, status, detail))
        if fix:
            self.fixes.append(fix)


def _has_dep(deps: list[str], pkg: str) -> bool:
    """Match by package name, ignoring version constraint."""
    pat = re.compile(r"^\s*" + re.escape(pkg) + r"(\s*[<>=!~]|\s*\[|\s*$)")
    return any(pat.match(d) for d in deps)


def _check_pypi(name: str) -> tuple[str, str]:
    """Check if a distribution exists on PyPI. Returns (status, detail).

    Fails gracefully when offline (5 s timeout). Absent distributions
    produce WARN (not FAIL) so audit reports stay informational.
    """
    try:
        import urllib.request
        import json as _json
        with urllib.request.urlopen(f"https://pypi.org/pypi/{name}/json", timeout=5) as resp:
            data = _json.loads(resp.read().decode())
        version = data.get("info", {}).get("version", "?")
        return "PASS", f"published on PyPI as {name} (latest: {version})"
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return "WARN", (
                "NOT published on PyPI — recommend publishing; "
                "see docs/conventions/distribution.md"
            )
        return "WARN", f"PyPI check failed: HTTP {e.code}"
    except Exception as e:
        return "WARN", f"PyPI check failed: {e}"



# Raw engine libraries that already have a viva-* process-bigraph wrapper. Importing one
# of these directly, without depending on its wrapper, re-implements a simulator the
# ecosystem already provides once. The wrapper repo itself is exempt (it owns the binding).
ENGINE_WRAPPERS = {
    "tellurium": "viva-tellurium", "roadrunner": "viva-tellurium", "libroadrunner": "viva-tellurium",
    "cobra": "viva-cobra", "basico": "viva-copasi", "amici": "viva-amici", "pysces": "viva-pysces",
    "simbio": "viva-simbio", "fipy": "viva-fipy", "dolfinx": "viva-fenics", "phreeqpython": "viva-phreeqc",
    "smoldyn": "viva-smoldyn", "pymunk": "viva-munk", "tyssue": "vivarium-tyssue", "cmaboss": "viva-maboss",
    "openmm": "viva-openmm", "readdy": "viva-readdy", "pymem3dg": "viva-mem3dg",
}
_IMPORT_RE = re.compile(r"^\s*(?:import|from)\s+([a-zA-Z_][\w]*)", re.MULTILINE)


def _reuse_findings(package_dirs, dep_names: set[str], project_name: str | None):
    """Raw engine imports in the package source that bypass an existing viva-* wrapper.

    Returns a list of (raw_module, wrapper, example_file). A repo that *is* the wrapper,
    or that already depends on the wrapper, is not flagged.
    """
    own = (project_name or "").replace("_", "-")
    found: dict[str, str] = {}
    for pkg_dir in package_dirs:
        for py in pkg_dir.rglob("*.py"):
            try:
                text = py.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for m in _IMPORT_RE.finditer(text):
                mod = m.group(1)
                if mod in ENGINE_WRAPPERS and mod not in found:
                    found[mod] = py.name
    out = []
    for raw, example in found.items():
        wrapper = ENGINE_WRAPPERS[raw]
        if own == wrapper:
            continue  # the wrapper legitimately owns this import
        if wrapper in dep_names or wrapper.replace("-", "_") in dep_names:
            continue  # already reuses the wrapper
        out.append((raw, wrapper, example))
    return out


def audit_repo(repo_path: Path, run_install: bool = True) -> AuditReport:
    report = AuditReport(target=str(repo_path))

    # 1. pyproject.toml
    pyproject_path = repo_path / "pyproject.toml"
    if not pyproject_path.exists():
        report.add("pyproject.toml", "FAIL", "missing", fix="Add a pyproject.toml with [project] table.")
        return report
    try:
        pyproject = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    except Exception as e:
        report.add("pyproject.toml", "FAIL", f"parse error: {e}")
        return report

    project = pyproject.get("project") or {}
    deps = project.get("dependencies") or []

    if not project:
        report.add("[project] table", "FAIL", "missing", fix="Add a [project] table with name, version, dependencies.")
        return report

    report.add("pyproject.toml", "PASS")

    # 2. bigraph-schema dep
    if _has_dep(deps, "bigraph-schema"):
        report.add("bigraph-schema dep", "PASS")
    else:
        report.add(
            "bigraph-schema dep", "FAIL",
            "not declared — package will not be picked up by allocate_core() auto-discovery",
            fix='Add "bigraph-schema>=1.8.1" to [project].dependencies',
        )

    # 3. process-bigraph dep
    if _has_dep(deps, "process-bigraph") or _has_dep(deps, "process_bigraph"):
        report.add("process-bigraph dep", "PASS")
    else:
        report.add(
            "process-bigraph dep", "WARN",
            "not declared — needed if you use Process/Step base classes",
            fix='Add "process-bigraph>=0.0.66" to [project].dependencies',
        )

    # 4. requires-python
    rp = project.get("requires-python")
    if rp:
        report.add("requires-python", "PASS", f"declared: {rp}")
    else:
        report.add(
            "requires-python", "WARN",
            "not declared — users may install on incompatible Python and see opaque errors",
            fix='Add `requires-python = ">=3.10"` (or tighter based on your wheel availability) to [project]',
        )

    # 5. Published on PyPI
    project_name = project.get("name")
    if project_name:
        status, detail = _check_pypi(project_name)
        report.add(
            "published on PyPI",
            status,
            detail,
            fix=(
                "See docs/conventions/distribution.md for trusted-publishing setup"
                if status == "WARN" else ""
            ),
        )

    # 6. Process/Step subclasses present
    package_dirs = []
    for child in repo_path.iterdir():
        if child.is_dir() and not child.name.startswith(".") and not child.name.startswith("_"):
            init = child / "__init__.py"
            if init.exists():
                package_dirs.append(child)
    found_subclasses = []
    for pkg_dir in package_dirs:
        for py in pkg_dir.rglob("*.py"):
            try:
                text = py.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            # Crude pattern — looks for class X(Process) or class X(Step) anywhere
            for cls_m in re.finditer(r"class\s+(\w+)\s*\(\s*(?:[\w.]+\.)?(Process|Step)\s*\)", text):
                found_subclasses.append(f"{cls_m.group(1)} ({cls_m.group(2)})")
    if found_subclasses:
        report.add(
            "Process/Step subclasses", "PASS",
            f"found {len(found_subclasses)}: {', '.join(found_subclasses[:5])}",
        )
    else:
        report.add(
            "Process/Step subclasses", "WARN",
            "no class inheriting from process_bigraph.Process or Step found "
            "(may be a composite-only package or use a custom base class)",
        )

    # 7. engine reuse — don't re-bind a raw engine that already has a viva-* wrapper
    dep_names = set()
    for spec in list(deps) + [d for ex in (project.get("optional-dependencies") or {}).values() for d in ex]:
        dep_names.add(re.split(r"[<>=!~\[ ]", spec)[0].strip())
    dep_names |= set(((pyproject.get("tool") or {}).get("uv") or {}).get("sources", {}).keys())
    reuse = _reuse_findings(package_dirs, dep_names, project.get("name"))
    if reuse:
        for raw, wrapper, example in reuse:
            report.add(
                f"engine reuse: {raw}", "WARN",
                f"binds {raw} directly ({example}) but does not depend on {wrapper} "
                f"— re-implements a simulator the ecosystem already wraps once",
                fix=f'Depend on "{wrapper}" and import the engine through it, instead of binding {raw} directly',
            )
    else:
        report.add("engine reuse", "PASS", "no raw engine bound that already has a viva-* wrapper")

    # 6. install smoke test
    if run_install:
        with tempfile.TemporaryDirectory() as tmp:
            venv = Path(tmp) / "venv"
            r = subprocess.run(
                ["uv", "venv", str(venv), "--python", sys.executable],
                capture_output=True, text=True,
            )
            if r.returncode != 0:
                report.add("pip install -e .", "WARN", "could not create ephemeral venv; skipped")
            else:
                try:
                    r = subprocess.run(
                        ["uv", "pip", "install", "--python", str(venv / "bin" / "python3"), "-e", str(repo_path)],
                        capture_output=True, text=True, timeout=180,
                    )
                except subprocess.TimeoutExpired:
                    report.add("pip install -e .", "FAIL", "install timed out after 180s")
                else:
                    if r.returncode == 0:
                        report.add("pip install -e .", "PASS")
                    else:
                        excerpt = (r.stderr or r.stdout).strip()[-500:]
                        report.add("pip install -e .", "FAIL", f"install failed; tail: {excerpt}")

    return report


def render_report(report: AuditReport) -> str:
    lines = [f"=== Audit: {report.target} ===", ""]
    counts: dict[str, int] = {"PASS": 0, "WARN": 0, "FAIL": 0}
    for c in report.checks:
        counts[c.status] = counts.get(c.status, 0) + 1
        detail = f"  — {c.detail}" if c.detail else ""
        lines.append(f"{c.name:35s} {c.status:5s}{detail}")
    lines.append("")
    lines.append("=== Summary ===")
    lines.append(f"PASS: {counts['PASS']}, WARN: {counts['WARN']}, FAIL: {counts['FAIL']}")
    if report.fixes:
        lines.append("")
        lines.append("Recommended fixes:")
        for f in report.fixes:
            lines.append(f"  - {f}")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        print("Usage: python -m viva_superpowers.package_audit <repo-path-or-name> [--no-install]")
        return 0
    target = argv[0]
    run_install = "--no-install" not in argv[1:]

    tmp_to_clean: Path | None = None

    if "/" in target or target.startswith(("~", ".")):
        repo_path = Path(target).expanduser().resolve()
    else:
        # Treat as vivarium-collective repo name
        tmp = Path(tempfile.mkdtemp(prefix="viva-audit-"))
        tmp_to_clean = tmp
        repo_path = tmp / target
        url = f"https://github.com/vivarium-collective/{target}.git"
        r = subprocess.run(
            ["git", "clone", "--depth", "1", url, str(repo_path)],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            print(f"failed to clone {url}: {r.stderr}")
            return 2

    if not repo_path.exists():
        print(f"path not found: {repo_path}")
        return 2

    try:
        report = audit_repo(repo_path, run_install=run_install)
        print(render_report(report))
        return 0 if all(c.status != "FAIL" for c in report.checks) else 1
    finally:
        if tmp_to_clean is not None and tmp_to_clean.exists():
            import shutil
            shutil.rmtree(tmp_to_clean, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
