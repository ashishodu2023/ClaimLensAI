"""
Integration test: Submit all sample claims to the running Evidence Review API.
Usage: python test_api.py [--url http://localhost:8000]
"""

import sys
import json
import argparse
import urllib.request
import urllib.error
sys.path.insert(0, "..")
from sample_data.sample_claims import SAMPLE_CLAIMS

def post_json(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def print_result(result: dict):
    verdict_colors = {
        "SUPPORTED": "\033[92m",    # green
        "CONTRADICTED": "\033[91m", # red
        "INSUFFICIENT": "\033[93m"  # yellow
    }
    reset = "\033[0m"
    verdict = result.get("verdict", "?")
    color = verdict_colors.get(verdict, "")

    print(f"\n{'='*60}")
    print(f"Claim ID:        {result['claim_id']}")
    print(f"Object Type:     {result['object_type']}")
    print(f"Extracted Claim: {result['extracted_claim']}")
    print(f"Verdict:         {color}{verdict}{reset} ({result['verdict_confidence']} confidence)")
    print(f"Issue Type:      {result['issue_type']}")
    print(f"Object Part:     {result['object_part']}")
    print(f"Severity:        {result['severity']}")
    print(f"Evidence OK:     {result['evidence_sufficient']}")
    print(f"Supporting IDs:  {result['supporting_image_ids']}")

    if result.get("risk_flags"):
        print(f"\nRisk Flags ({len(result['risk_flags'])}):")
        for flag in result["risk_flags"]:
            sev_color = "\033[91m" if flag["severity"] == "high" else "\033[93m"
            print(f"  [{sev_color}{flag['severity'].upper()}{reset}] {flag['flag_type']}: {flag['description']}")

    print(f"\nJustification:   {result['justification']}")
    print(f"Image Summary:   {result['image_analysis_summary']}")
    print(f"Reviewer Notes:  {result['reviewer_notes']}")
    print(f"Processed At:    {result['processed_at']}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    args = parser.parse_args()
    base = args.url.rstrip("/")

    # Health check
    print(f"Connecting to {base}...")
    try:
        with urllib.request.urlopen(f"{base}/health", timeout=5) as r:
            health = json.loads(r.read())
            print(f"Service: {health['service']} v{health['version']} — OK\n")
    except Exception as e:
        print(f"Health check failed: {e}")
        sys.exit(1)

    results = []
    for claim in SAMPLE_CLAIMS:
        print(f"\nSubmitting claim {claim['claim_id']}...")
        try:
            result = post_json(f"{base}/api/review", claim)
            results.append(result)
            print_result(result)
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            print(f"  HTTP {e.code}: {body}")
        except Exception as e:
            print(f"  Error: {e}")

    # Save results
    with open("test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n\nResults saved to test_results.json")
    print(f"Total claims processed: {len(results)}/{len(SAMPLE_CLAIMS)}")

    # Summary
    verdicts = [r["verdict"] for r in results]
    print(f"\nVerdict summary:")
    for v in ["SUPPORTED", "CONTRADICTED", "INSUFFICIENT"]:
        print(f"  {v}: {verdicts.count(v)}")


if __name__ == "__main__":
    main()
