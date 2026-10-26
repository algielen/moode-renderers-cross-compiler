"""Select reviewed, unpublished package recipes; never infer license clearance."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def identity(profile, package):
    return {"target": profile["target"], "distribution": profile["distribution"],
            "architecture": profile["architecture"], "package": package}


def key(recipe):
    return json.dumps(recipe, sort_keys=True, separators=(",", ":"))


def load():
    return json.loads((ROOT / "compiler/release-policy.json").read_text())


def profiles_for_policy():
    return {p.stem: json.loads(p.read_text()) for p in (ROOT / "profiles").glob("*.json")}


def cleared(profile, renderer, policy=None, root=ROOT):
    policy = load() if policy is None else policy
    if policy["schema"] != 1:
        raise ValueError("Unknown release policy schema")
    for name, digest in policy["reviewed_build_inputs"].items():
        data = (root / name).read_text(encoding="utf-8-sig").replace("\r\n", "\n").encode()
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError(f"Release clearance requires review of changed build input: {name}")
    approved = {key(item["recipe"]) for item in policy["approvals"] if item["status"] == "cleared"}
    packages = profile["renderers"].get(renderer, {}).get("packages", [])
    return bool(packages) and all(key(identity(profile, package)) in approved for package in packages)


def plan(version, available, policy=None, root=ROOT):
    policy = load() if policy is None else policy
    if version not in available:
        raise ValueError("Unknown release profile")
    selected, reused, blocked = [], [], []
    for renderer, config in available[version]["renderers"].items():
        if not cleared(available[version], renderer, policy, root):
            blocked.append(renderer)
            continue
        recipes = [identity(available[version], package) for package in config["packages"]]
        receipts = [next((item for item in policy["published"] if key(item["recipe"]) == key(recipe)), None)
                    for recipe in recipes]
        if all(receipts):
            reused.extend({"renderer": renderer, "package": recipe["package"]["name"],
                           "release": receipt["release"], "profile": receipt["profile"]}
                          for recipe, receipt in zip(recipes, receipts))
            continue
        if any(receipts):
            raise ValueError("Mixed published/new components require package-level delta support")
        # Build one representative of this recipe, even when a later matching profile is requested.
        matching = [v for v, p in available.items() if renderer in p["renderers"] and
                    [identity(p, package) for package in p["renderers"][renderer]["packages"]] == recipes]
        representative = min(matching, key=lambda v: tuple(map(int, v.split("."))))
        selected.append({"renderer": renderer, "versions": [representative],
                         "compatible_profiles": sorted(matching, key=lambda v: tuple(map(int, v.split("."))))})
    representative = min((s["versions"][0] for s in selected),
                         key=lambda v: tuple(map(int, v.split("."))), default=version)
    ready = [s for s in selected if s["versions"] == [representative]]
    return {"profile": representative, "matrix": {"include": ready}, "reused": reused,
            "blocked": blocked, "queued": [s for s in selected if s not in ready]}
