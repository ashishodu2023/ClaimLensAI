"""
Sample claim payloads for testing the Evidence Review System.
Images use small real-world test patterns (actual base64 PNG data).
In production, replace base64_data with actual damage photos.
"""

# Minimal valid 1x1 red PNG for test scaffolding
# In real use, these would be actual damage photos from the claim
TINY_RED_PNG = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8"
    "z8BQDwADhQGAWjR9awAAAABJRU5ErkJggg=="
)

SAMPLE_CLAIMS = [
    {
        "claim_id": "CLM-2024-CAR-001",
        "object_type": "car",
        "conversation": [
            {"role": "user", "text": "I need to file a claim for damage to my car."},
            {"role": "agent", "text": "I can help you with that. What type of damage occurred?"},
            {"role": "user", "text": "Someone hit my rear bumper in a parking lot. There's a significant dent and some paint scratches on the right side of the bumper."},
            {"role": "agent", "text": "I'm sorry to hear that. Please upload photos of the damage."},
            {"role": "user", "text": "Here are the photos I took right after the incident."}
        ],
        "images": [
            {
                "image_id": "IMG-001-A",
                "base64_data": TINY_RED_PNG,
                "media_type": "image/png"
            },
            {
                "image_id": "IMG-001-B",
                "base64_data": TINY_RED_PNG,
                "media_type": "image/png"
            }
        ],
        "user_history": {
            "previous_claims": 2,
            "approved_claims": 2,
            "rejected_claims": 0,
            "fraud_flags": 0,
            "account_age_days": 730,
            "risk_score": 0.15
        },
        "minimum_evidence_required": 1
    },
    {
        "claim_id": "CLM-2024-LAPTOP-002",
        "object_type": "laptop",
        "conversation": [
            {"role": "user", "text": "My laptop screen cracked after it fell off my desk."},
            {"role": "agent", "text": "How did the fall occur and what exactly is damaged?"},
            {"role": "user", "text": "It fell about 3 feet onto hardwood floor. The screen has a large crack across the middle and some pixels are dead. The corner of the chassis is also bent."},
            {"role": "agent", "text": "Please provide photos showing the screen damage and the physical impact point."}
        ],
        "images": [
            {
                "image_id": "IMG-002-A",
                "base64_data": TINY_RED_PNG,
                "media_type": "image/png"
            }
        ],
        "user_history": {
            "previous_claims": 5,
            "approved_claims": 3,
            "rejected_claims": 2,
            "fraud_flags": 1,
            "account_age_days": 365,
            "risk_score": 0.62
        },
        "minimum_evidence_required": 2
    },
    {
        "claim_id": "CLM-2024-PKG-003",
        "object_type": "package",
        "conversation": [
            {"role": "user", "text": "My package arrived severely damaged."},
            {"role": "agent", "text": "What does the damage look like?"},
            {"role": "user", "text": "The box is completely crushed on one side and the contents — a ceramic vase — is broken into pieces. The packaging tape looks like it was cut and resealed too."},
            {"role": "agent", "text": "That sounds like it may have been mishandled. Please upload images of the outer packaging and the damaged contents."}
        ],
        "images": [
            {
                "image_id": "IMG-003-A",
                "base64_data": TINY_RED_PNG,
                "media_type": "image/png"
            },
            {
                "image_id": "IMG-003-B",
                "base64_data": TINY_RED_PNG,
                "media_type": "image/png"
            },
            {
                "image_id": "IMG-003-C",
                "base64_data": TINY_RED_PNG,
                "media_type": "image/png"
            }
        ],
        "user_history": {
            "previous_claims": 0,
            "approved_claims": 0,
            "rejected_claims": 0,
            "fraud_flags": 0,
            "account_age_days": 180,
            "risk_score": 0.05
        },
        "minimum_evidence_required": 1
    }
]

if __name__ == "__main__":
    import json
    print(json.dumps(SAMPLE_CLAIMS[0], indent=2))
