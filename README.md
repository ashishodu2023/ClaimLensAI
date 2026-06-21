# ClaimLens — AI Damage Claim Intelligence

An AI-powered damage claim verification system using Claude Vision to analyze images and determine whether submitted evidence **supports**, **contradicts**, or is **insufficient** to verify a damage claim across cars, laptops, and packages.

---

## Architecture

```mermaid
flowchart TD
    A([Claim Request\nclaim_id · object_type · images · conversation · user_history])

    subgraph INGRESS["Input Validation"]
        direction TB
        V1{object_type valid?\ncar · laptop · package}
        V2{images present?}
        V3{conversation not empty?}
    end

    subgraph EXTRACT["Step 1 — Claim Extraction"]
        E1[["Claude Sonnet — Text\nextract_claim_from_conversation"]]
        E2["Extracted claim sentence"]
    end

    subgraph VISION["Step 2 — Per-Image Vision Analysis"]
        direction LR
        IMG1[["Image 1\nanalyze_image_with_vision"]]
        IMG2[["Image 2\nanalyze_image_with_vision"]]
        IMGN[["Image N\nanalyze_image_with_vision"]]
        PERIMG["Per-image JSON\nverdict · issue_type · object_part\nimage_quality · authenticity"]
    end

    subgraph AGGREGATE["Step 3 — Verdict Aggregation"]
        direction TB
        AGG1{Any image\nCONTRADICTED?}
        AGG2{count SUPPORTED\n>= min_required?}
        R1["CONTRADICTED\nevidence_sufficient=true"]
        R2["SUPPORTED\nevidence_sufficient=true"]
        R3["INSUFFICIENT\nevidence_sufficient=false"]
    end

    subgraph AGENT["Step 4 — Reasoning Agent"]
        RA[["Claude Sonnet — Text\ncross-image holistic review"]]
        RB["chain_of_thought\noverride if needed"]
    end

    subgraph FLAGS["Step 5 — Risk Flag Engine"]
        direction LR
        F1["image_quality\npoor / fair"]
        F2["mismatch\nwrong object type"]
        F3["authenticity\nediting signals"]
        F4["user_history\nfraud · rejection rate"]
    end

    subgraph OUTPUT["Final Response — EvidenceReviewResult"]
        direction TB
        OUT1["verdict · confidence · severity\nissue_type · object_part · supporting_image_ids"]
        OUT2["risk_flags · justification · chain_of_thought\nreviewer_notes · processed_at · processing_ms"]
    end

    ERR([400 Bad Request])

    A --> INGRESS
    V1 -->|invalid| ERR
    V2 -->|missing| ERR
    V3 -->|empty| ERR
    V1 -->|valid| E1
    V2 -->|ok| E1
    V3 -->|ok| E1
    E1 --> E2
    E2 --> IMG1
    E2 --> IMG2
    E2 --> IMGN
    IMG1 --> PERIMG
    IMG2 --> PERIMG
    IMGN --> PERIMG
    PERIMG --> AGG1
    AGG1 -->|yes| R1
    AGG1 -->|no| AGG2
    AGG2 -->|yes| R2
    AGG2 -->|no| R3
    R1 --> RA
    R2 --> RA
    R3 --> RA
    RA --> RB
    RB --> F1
    F1 --> F2 --> F3 --> F4
    F4 --> OUT1
    F4 --> OUT2
```

---

## Verdict Decision Logic

| Condition | Result |
|---|---|
| Any image returns `CONTRADICTED` | **CONTRADICTED** (overrides all support) |
| `count(SUPPORTED) >= minimum_evidence_required` | **SUPPORTED** |
| Otherwise | **INSUFFICIENT** |

> Contradiction takes unconditional priority. This prevents cherry-picked evidence where one clean image is submitted alongside damage photos of a different vehicle.

---

## Pipeline — 5 Steps

| Step | What happens | Claude calls |
|---|---|---|
| **1. Claim extraction** | Conversation → 1-sentence damage claim (cached) | 1 text call |
| **2. Vision analysis** | All images analyzed in parallel via `asyncio.gather` | N vision calls |
| **3. Aggregation** | Pure Python — contradiction override, min evidence gate | 0 |
| **4. Reasoning Agent** | Holistic cross-image review, can override preliminary verdict | 1 text call |
| **5. Risk flags** | Post-verdict — structurally cannot change the verdict | 0 |

---

## Risk Flag Categories

| Flag type | Severity | Trigger |
|---|---|---|
| `image_quality` | low / high | Image is poor or fair quality |
| `mismatch` | high | Image shows wrong object type |
| `authenticity` | high | Visual signs of editing or staging detected |
| `user_history` | medium / high | Prior fraud flags, elevated risk score, or >50% rejection rate |

> Risk flags run **after** verdict aggregation and **cannot** change the verdict. Informational only.

---

## WhatsApp Intake

ClaimLens supports end-to-end claim filing via WhatsApp — no portal, no app download.

```
Customer texts "hi"
      ↓
Bot asks: car / laptop / package?
      ↓
Bot asks: describe the damage
      ↓
Customer sends 1–5 photos → replies DONE
      ↓
AI pipeline runs in background (~30s)
      ↓
Bot replies with verdict + severity + next steps
```

See [WHATSAPP_SETUP.md](./WHATSAPP_SETUP.md) for Twilio configuration.

---

## Project Structure

```
evidence-review/
├── backend/
│   ├── app.py                  # FastAPI — full AI pipeline
│   ├── whatsapp.py             # Twilio WhatsApp intake
│   ├── server.py               # Production entry (uvloop + httptools)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── Header.jsx
│   │   │   ├── ClaimForm.jsx
│   │   │   ├── ConversationBuilder.jsx
│   │   │   ├── ImageUploader.jsx
│   │   │   ├── MermaidDiagram.jsx
│   │   │   └── ResultPanel.jsx
│   │   ├── pages/
│   │   │   ├── ReviewPage.jsx
│   │   │   └── ArchitecturePage.jsx
│   │   └── utils/
│   │       ├── api.js
│   │       └── helpers.js
│   ├── package.json
│   └── vite.config.js
├── WHATSAPP_SETUP.md
├── docker-compose.yml
└── README.md
```

---

## Setup

### Backend

```bash
pip install -r backend/requirements.txt
export ANTHROPIC_API_KEY=your_key_here
uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:3000
```

### Docker

```bash
docker-compose up
# Open http://localhost:8000
```

---

## API

### POST /api/review

```json
{
  "claim_id": "CLM-2024-001",
  "object_type": "car",
  "conversation": [
    { "role": "user", "text": "My rear bumper is dented after a parking lot collision." },
    { "role": "agent", "text": "Please upload photos of the damage." }
  ],
  "images": [
    { "image_id": "IMG-001", "base64_data": "<base64>", "media_type": "image/jpeg" }
  ],
  "user_history": {
    "previous_claims": 2, "approved_claims": 2, "rejected_claims": 0,
    "fraud_flags": 0, "account_age_days": 730, "risk_score": 0.15
  },
  "minimum_evidence_required": 1
}
```

### Response

```json
{
  "claim_id": "CLM-2024-001",
  "verdict": "SUPPORTED",
  "verdict_confidence": "high",
  "severity": "moderate",
  "issue_type": "dent",
  "object_part": "rear bumper",
  "supporting_image_ids": ["IMG-001"],
  "risk_flags": [],
  "justification": "IMG-001 shows a clear dent on the rear bumper with paint transfer.",
  "chain_of_thought": "Single image clearly shows rear bumper dent matching the described collision.",
  "overrode_preliminary": false,
  "evidence_sufficient": true,
  "processed_at": "2024-01-15T10:31:04Z",
  "processing_ms": 2847
}
```

### POST /api/batch-review

Array of claim requests. Returns `{ results, errors, total }`.

### POST /whatsapp/webhook

Twilio webhook for WhatsApp intake. See [WHATSAPP_SETUP.md](./WHATSAPP_SETUP.md).

---

## Supported Object Types

| Type | Example issues |
|---|---|
| `car` | dent, scratch, crack, glass_shatter, broken_part |
| `laptop` | crack, broken_part, water_damage, missing_part |
| `package` | crushed_packaging, torn_packaging, water_damage, stain |

---

## Design Decisions

1. **Images are the source of truth.** User history produces flags only — never changes the verdict.
2. **Contradiction overrides everything.** One contradicting image beats any number of supporting images.
3. **Deterministic step before agent.** Pure Python aggregation provides a safe fallback if the agent fails.
4. **Risk flags are post-verdict.** Structurally impossible for flags to influence the verdict.
5. **Prompt injection defense.** Text instructions in images are flagged and ignored; visual evidence decides.
6. **Multilingual by default.** Claim conversations and image text in any language are handled natively.