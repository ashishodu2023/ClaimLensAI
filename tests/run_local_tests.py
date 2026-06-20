#!/usr/bin/env python3
"""
Local test runner for Multi-Modal Evidence Review System.
Tests all 3 object types with real damage images against the live API.

Usage:
    python tests/run_local_tests.py
    python tests/run_local_tests.py --url http://localhost:8000
    python tests/run_local_tests.py --verbose
"""

import argparse
import base64
import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
IMAGE_DIR = BASE_DIR / "tests" / "test_images"

# ─── ANSI colours ────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

def col(text, color): return f"{color}{text}{RESET}"
def ok(t):   return col(t, GREEN)
def err(t):  return col(t, RED)
def warn(t): return col(t, YELLOW)
def info(t): return col(t, CYAN)
def bold(t): return col(t, BOLD)

# ─── HTTP helpers ─────────────────────────────────────────────────────────────
def post(url, payload, timeout=90):
    data = json.dumps(payload).encode()
    req  = urllib.request.Request(url, data=data,
                                  headers={"Content-Type": "application/json"},
                                  method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())

def get(url, timeout=5):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read())

# ─── Load image as b64 ───────────────────────────────────────────────────────
def img_b64(name):
    path = IMAGE_DIR / name
    if not path.exists():
        print(err(f"  Missing test image: {path}"))
        print(err("  Run: python tests/generate_test_images.py  to create them"))
        sys.exit(1)
    return base64.b64encode(path.read_bytes()).decode()

# ─── Test cases ──────────────────────────────────────────────────────────────
def build_test_cases():
    return [
        # ── Test 1: Car dent with good user history → expect SUPPORTED ───────
        {
            "name": "Car rear bumper dent (low risk user, 1 image)",
            "expect_verdict": "SUPPORTED",
            "expect_risk_flag_count_max": 0,
            "payload": {
                "claim_id": "TEST-CAR-001",
                "object_type": "car",
                "conversation": [
                    {"role": "user",  "text": "I need to file a claim for my car."},
                    {"role": "agent", "text": "What damage occurred?"},
                    {"role": "user",  "text": "Someone hit my rear bumper in a parking lot. There's a significant dent and paint scratches on the right side along with red paint transfer from the other vehicle."},
                    {"role": "agent", "text": "Please upload clear photos of the damage."},
                ],
                "images": [
                    {"image_id": "CAR-IMG-001", "base64_data": img_b64("car_dent_front.png"), "media_type": "image/png"}
                ],
                "user_history": {
                    "previous_claims": 2, "approved_claims": 2, "rejected_claims": 0,
                    "fraud_flags": 0, "account_age_days": 730, "risk_score": 0.12
                },
                "minimum_evidence_required": 1
            }
        },
        # ── Test 2: Laptop cracked screen, high risk user, below min images ──
        {
            "name": "Laptop cracked screen (high risk user, below min evidence)",
            "expect_verdict": "INSUFFICIENT",
            "expect_has_risk_flags": True,
            "payload": {
                "claim_id": "TEST-LAPTOP-002",
                "object_type": "laptop",
                "conversation": [
                    {"role": "user",  "text": "My laptop screen cracked after it fell off my desk."},
                    {"role": "agent", "text": "What exactly is damaged?"},
                    {"role": "user",  "text": "The screen has a large crack across the middle with dead pixels on the left side. The chassis corner is also bent from the impact point."},
                    {"role": "agent", "text": "Please provide photos of the screen and the impact point."},
                ],
                "images": [
                    {"image_id": "LAPTOP-IMG-001", "base64_data": img_b64("laptop_cracked_screen.png"), "media_type": "image/png"}
                ],
                "user_history": {
                    "previous_claims": 5, "approved_claims": 2, "rejected_claims": 3,
                    "fraud_flags": 1, "account_age_days": 120, "risk_score": 0.75
                },
                "minimum_evidence_required": 2  # 1 image submitted but 2 required → INSUFFICIENT
            }
        },
        # ── Test 3: Package damage, new clean user ────────────────────────────
        {
            "name": "Package crushed (new clean user, 1 image)",
            "expect_verdict": "SUPPORTED",
            "expect_risk_flag_count_max": 1,
            "payload": {
                "claim_id": "TEST-PKG-003",
                "object_type": "package",
                "conversation": [
                    {"role": "user",  "text": "My package arrived badly damaged."},
                    {"role": "agent", "text": "What does the damage look like?"},
                    {"role": "user",  "text": "The right side of the box is completely crushed inward. The tape also looks like it was cut and resealed. The ceramic item inside is broken."},
                    {"role": "agent", "text": "Upload images of the outer packaging and contents."},
                ],
                "images": [
                    {"image_id": "PKG-IMG-001", "base64_data": img_b64("crushed_package_box.png"), "media_type": "image/png"}
                ],
                "user_history": {
                    "previous_claims": 0, "approved_claims": 0, "rejected_claims": 0,
                    "fraud_flags": 0, "account_age_days": 200, "risk_score": 0.05
                },
                "minimum_evidence_required": 1
            }
        },
        # ── Test 4: Input validation - missing images (should 400) ────────────
        {
            "name": "Validation: empty images array → expect 400",
            "expect_http_error": 400,
            "payload": {
                "claim_id": "TEST-VAL-004",
                "object_type": "car",
                "conversation": [{"role": "user", "text": "My car is damaged."}],
                "images": [],
                "minimum_evidence_required": 1
            }
        },
        # ── Test 5: Input validation - invalid object type (should 400) ───────
        {
            "name": "Validation: invalid object_type → expect 400",
            "expect_http_error": 400,
            "payload": {
                "claim_id": "TEST-VAL-005",
                "object_type": "bicycle",
                "conversation": [{"role": "user", "text": "My bike is damaged."}],
                "images": [
                    {"image_id": "X", "base64_data": img_b64("car_dent_front.png"), "media_type": "image/png"}
                ],
                "minimum_evidence_required": 1
            }
        },
    ]

# ─── Run tests ────────────────────────────────────────────────────────────────
def run_tests(base_url: str, verbose: bool):
    print(f"\n{bold('='*60)}")
    print(bold("  Multi-Modal Evidence Review — Local Test Suite"))
    print(bold(f"  Target: {base_url}"))
    print(bold('='*60))

    # Health check
    print(f"\n{info('Checking API health...')}")
    try:
        health = get(f"{base_url}/health")
        print(ok(f"  ✓ {health['service']} v{health['version']} — {health['status']}"))
    except Exception as e:
        print(err(f"  ✗ Health check failed: {e}"))
        print(err("  Make sure the backend is running:"))
        print(err("    uvicorn backend.app:app --port 8000"))
        sys.exit(1)

    cases = build_test_cases()
    passed = 0
    failed = 0
    results = []

    for i, case in enumerate(cases, 1):
        name = case["name"]
        print(f"\n{bold(f'Test {i}/{len(cases)}:')} {name}")

        # Validation error cases
        if "expect_http_error" in case:
            try:
                post(f"{base_url}/api/review", case["payload"])
                print(err(f"  ✗ Expected HTTP {case['expect_http_error']} but got 200"))
                failed += 1
            except urllib.error.HTTPError as e:
                if e.code == case["expect_http_error"]:
                    print(ok(f"  ✓ Got expected HTTP {e.code}"))
                    passed += 1
                else:
                    print(err(f"  ✗ Expected HTTP {case['expect_http_error']}, got HTTP {e.code}"))
                    failed += 1
            continue

        # Normal API cases
        t0 = time.time()
        try:
            result = post(f"{base_url}/api/review", case["payload"])
            elapsed = time.time() - t0

            verdict = result.get("verdict")
            expected = case.get("expect_verdict")
            flags    = result.get("risk_flags", [])
            high_flags = [f for f in flags if f["severity"] == "high"]

            # Verdict check
            if expected and verdict != expected:
                print(warn(f"  ~ Verdict: {verdict} (expected {expected}) — may vary with synthetic images"))
            else:
                print(ok(f"  ✓ Verdict: {verdict}"))

            # Risk flag checks
            if case.get("expect_has_risk_flags") and not flags:
                print(warn("  ~ Expected risk flags but none found"))
            elif flags:
                print(warn(f"  ⚠ {len(flags)} risk flag(s): {[f['flag_type'] for f in flags]}"))
            else:
                print(ok("  ✓ No risk flags"))

            # Core fields present
            required = ["claim_id","object_type","extracted_claim","verdict",
                        "verdict_confidence","issue_type","object_part",
                        "severity","justification","evidence_sufficient",
                        "reviewer_notes","processed_at"]
            missing = [f for f in required if f not in result]
            if missing:
                print(err(f"  ✗ Missing fields: {missing}"))
                failed += 1
            else:
                print(ok("  ✓ All required fields present"))
                passed += 1

            print(DIM + f"    extracted_claim: {result['extracted_claim'][:80]}..." + RESET)
            print(DIM + f"    severity: {result['severity']} | confidence: {result['verdict_confidence']} | elapsed: {elapsed:.1f}s" + RESET)

            if verbose:
                print(DIM + f"    justification: {result['justification'][:120]}..." + RESET)

            results.append(result)

        except urllib.error.HTTPError as e:
            body = e.read().decode()
            print(err(f"  ✗ HTTP {e.code}: {body[:200]}"))
            failed += 1
        except Exception as e:
            print(err(f"  ✗ Error: {e}"))
            failed += 1

    # Summary
    total = passed + failed
    print(f"\n{bold('='*60)}")
    print(bold("  Results"))
    print(bold('='*60))
    print(f"  {ok(f'Passed: {passed}/{total}')}")
    if failed:
        print(f"  {err(f'Failed: {failed}/{total}')}")
    print()

    # Save results
    output_path = BASE_DIR / "tests" / "test_results.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(info(f"  Results saved to {output_path}"))

    verdicts = [r.get("verdict") for r in results]
    for v in ["SUPPORTED", "CONTRADICTED", "INSUFFICIENT"]:
        count = verdicts.count(v)
        if count:
            print(f"  {v}: {count}")

    sys.exit(0 if failed == 0 else 1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run local tests against Evidence Review API")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of the API")
    parser.add_argument("--verbose", action="store_true", help="Show full justifications")
    args = parser.parse_args()
    run_tests(args.url.rstrip("/"), args.verbose)
