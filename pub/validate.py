"""
Content model validator.

Checks that pub/content-model.yaml is internally consistent and that all
referenced post directories and required files exist on disk.

Usage:
    python pub/validate.py
    python pub/validate.py --verbose
"""

import os
import sys
import yaml
import argparse

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB_DIR = os.path.join(REPO_ROOT, "pub")
CONTENT_MODEL_PATH = os.path.join(PUB_DIR, "content-model.yaml")
POSTS_DIR = os.path.join(PUB_DIR, "posts")
SERIES_DIR = os.path.join(PUB_DIR, "series")

REQUIRED_POST_FILES = ["meta.yaml", "master.md"]
OPTIONAL_POST_FILES = ["github.md", "linkedin.md", "x-twitter.md"]

REQUIRED_SERIES_DIRS = [
    "01-tool-reality",
    "02-deterministic-enforcement",
    "03-supply-chain",
    "04-forensics",
]


def load_content_model():
    with open(CONTENT_MODEL_PATH) as f:
        return yaml.safe_load(f)


def check_content_model_valid(model, verbose):
    errors = []

    # Version field
    if model.get("version") != 1:
        errors.append(f"content-model.yaml: expected version: 1, got {model.get('version')}")

    # Pillar IDs referenced in posts exist
    pillar_ids = {p["id"] for p in model.get("pillars", [])}
    for post in model.get("posts", []):
        for pid in post.get("pillars", []):
            if pid not in pillar_ids:
                errors.append(f"Post '{post['slug']}': pillar '{pid}' not defined in pillars section")

    # Series IDs referenced in posts exist
    series_ids = {s["id"] for s in model.get("series", [])}
    for post in model.get("posts", []):
        sid = post.get("series")
        if sid and sid not in series_ids:
            errors.append(f"Post '{post['slug']}': series '{sid}' not defined in series section")

    # Posts referenced in series exist in posts section
    post_slugs = {p["slug"] for p in model.get("posts", [])}
    for series in model.get("series", []):
        for slug in series.get("posts", []):
            if slug not in post_slugs:
                errors.append(f"Series '{series['id']}': post '{slug}' not in posts section")

    if verbose:
        print(f"  Pillars defined: {sorted(pillar_ids)}")
        print(f"  Series defined: {sorted(series_ids)}")
        print(f"  Posts declared: {len(post_slugs)}")

    return errors


def check_post_directories(model, verbose):
    errors = []
    warnings = []

    for post in model.get("posts", []):
        slug = post["slug"]
        post_dir = os.path.join(POSTS_DIR, slug)

        if not os.path.isdir(post_dir):
            errors.append(f"Post '{slug}': directory not found at {post_dir}")
            continue

        for required in REQUIRED_POST_FILES:
            path = os.path.join(post_dir, required)
            if not os.path.isfile(path):
                errors.append(f"Post '{slug}': required file missing: {required}")

        for optional in OPTIONAL_POST_FILES:
            path = os.path.join(post_dir, optional)
            if not os.path.isfile(path):
                warnings.append(f"Post '{slug}': optional file missing: {optional}")

        if verbose:
            existing = [f for f in REQUIRED_POST_FILES + OPTIONAL_POST_FILES
                        if os.path.isfile(os.path.join(post_dir, f))]
            print(f"  [{slug}] files: {existing}")

    return errors, warnings


def check_series_directories(verbose):
    errors = []
    for name in REQUIRED_SERIES_DIRS:
        series_dir = os.path.join(SERIES_DIR, name)
        meta_path = os.path.join(series_dir, "meta.yaml")
        if not os.path.isdir(series_dir):
            errors.append(f"Series directory missing: pub/series/{name}/")
        elif not os.path.isfile(meta_path):
            errors.append(f"Series meta missing: pub/series/{name}/meta.yaml")
        elif verbose:
            print(f"  Series [{name}]: ok")
    return errors


def check_artifact_references(model, verbose):
    warnings = []
    for post in model.get("posts", []):
        slug = post["slug"]
        for draw in post.get("draws_from", []):
            path = os.path.join(REPO_ROOT, draw)
            if not os.path.exists(path):
                warnings.append(f"Post '{slug}': draws_from '{draw}' not found on disk")
    return warnings


def main():
    parser = argparse.ArgumentParser(description="Validate pub/content-model.yaml")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    print(f"Validating {CONTENT_MODEL_PATH}")

    try:
        model = load_content_model()
    except Exception as e:
        print(f"ERROR: could not load content-model.yaml: {e}")
        sys.exit(1)

    all_errors = []
    all_warnings = []

    if args.verbose:
        print("\n[1] Content model internal consistency")
    errors = check_content_model_valid(model, args.verbose)
    all_errors.extend(errors)

    if args.verbose:
        print("\n[2] Post directories")
    errors, warnings = check_post_directories(model, args.verbose)
    all_errors.extend(errors)
    all_warnings.extend(warnings)

    if args.verbose:
        print("\n[3] Series directories")
    errors = check_series_directories(args.verbose)
    all_errors.extend(errors)

    if args.verbose:
        print("\n[4] Artifact references (draws_from)")
    warnings = check_artifact_references(model, args.verbose)
    all_warnings.extend(warnings)

    print()
    if all_errors:
        print(f"ERRORS ({len(all_errors)}):")
        for e in all_errors:
            print(f"  ✗ {e}")
    if all_warnings:
        print(f"WARNINGS ({len(all_warnings)}):")
        for w in all_warnings:
            print(f"  ~ {w}")

    if not all_errors and not all_warnings:
        posts = model.get("posts", [])
        series = model.get("series", [])
        print(f"OK — {len(posts)} posts across {len(series)} series, all files present")
        sys.exit(0)
    elif not all_errors:
        posts = model.get("posts", [])
        print(f"OK (with warnings) — {len(posts)} posts, {len(all_warnings)} optional files missing")
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
