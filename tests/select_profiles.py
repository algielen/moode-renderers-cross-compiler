"""Plan expensive CI checks from the event's Git baseline."""

import argparse
import json
import os
from pathlib import Path
import subprocess
from ci_verification import matrix


def git(*args):
    return subprocess.check_output(["git", *args], text=True).strip()


def baseline(event, event_name, head):
    if event_name == "pull_request":
        return git("merge-base", event["pull_request"]["base"]["sha"], head)
    if event_name == "push" and not event.get("ref", "").startswith("refs/tags/"):
        before = event.get("before", "")
        return before if before and set(before) != {"0"} else None
    # Tags/manual runs compare with the preceding release, excluding this tag.
    try:
        return git("describe", "--tags", "--match", "v[0-9]*", "--abbrev=0", head + "^")
    except subprocess.CalledProcessError:
        return None


def select(paths, available, full=False, release=False, profile_only=False, release_profile="10.2.0"):
    if (profile_only or release) and release_profile not in available:
        raise ValueError("Selected release profile is unavailable")
    if profile_only:
        return {"versions": [release_profile], "build": True, "full": False}
    shared = any(p == "Dockerfile" or p == ".dockerignore"
                 or p.startswith("compiler/") or p.startswith(".github/workflows/")
                 or (p.startswith("tests/") and p != "tests/test_cli.py") for p in paths)
    full = full or shared
    versions = set(available) if full else {
        version for version in available if f"profiles/{version}.json" in paths
    }
    # Releases must still produce their advertised default download bundle.
    if release:
        versions.add(release_profile)
    return {"versions": sorted(versions), "build": bool(versions), "full": full}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", default=os.environ.get("GITHUB_EVENT_PATH"), required=False)
    parser.add_argument("--event-name", default=os.environ.get("GITHUB_EVENT_NAME", "push"))
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--profile-only", action="store_true", help="Smoke-test only the selected release profile")
    parser.add_argument("--release-profile", default="10.2.0")
    args = parser.parse_args()
    if args.full and args.profile_only:
        parser.error("--full and --profile-only cannot be combined")
    event = json.loads(Path(args.event).read_text())
    base = baseline(event, args.event_name, args.head)
    paths = git("diff", "--name-only", base, args.head).splitlines() if base else []
    available = [p.stem for p in Path("profiles").glob("*.json")]
    plan = select(paths, available, full=args.full or base is None,
                  release=event.get("ref", os.environ.get("GITHUB_REF", "")).startswith("refs/tags/v"),
                  profile_only=args.profile_only, release_profile=args.release_profile)
    plan["profile_only"] = args.profile_only
    plan["release_profile"] = args.release_profile
    plan["matrix"] = matrix(plan["versions"], {
        p.stem: json.loads(p.read_text()) for p in Path("profiles").glob("*.json")})
    print(json.dumps({"base": base, **plan}), flush=True)
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as output:
            for key, value in plan.items():
                output.write(f"{key}={json.dumps(value)}\n")


if __name__ == "__main__":
    main()
