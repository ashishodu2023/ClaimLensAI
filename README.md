# Multi-Modal Damage Claim Review System

An AI-powered damage claim verification system using Claude Vision to analyze images and determine whether submitted evidence **supports**, **contradicts**, or is **insufficient** to verify a user's damage claim.

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
        E1[["Claude Sonnet — Text\nextract_claim_from_conversation()"]]
        E2(["Extracted claim sentence"])
    end

    subgraph VISION["Step 2 — Per-Image Vision Analysis"]
        direction LR
        IMG1[["Image 1\nanalyze_image_with_vision()"]]
        IMG2[["Image 2\nanalyze_image_with_vision()"]]
        IMGN[["Image N..."])
        PERIMG(["Per-image JSON\nverdict · issue_type · object_part\nimage_quality · authenticity"])
    end

    subgraph AGGREGATE["Step 3 — Verdict Aggregation"]
        direction TB
        AGG1{"Any image\nCONTRADICTED?"}
        AGG2{"count SUPPORTED\n>= min_required?"}
        R1(["CONTRADICTED\nevidence_sufficient=true"])
        R2(["SUPPORTED\nevidence_sufficient=true"])
        R3(["INSUFFICIENT\nevidence_sufficient=false"])
    end

    subgraph FLAGS["Step 4 — Risk Flag Engine"]
        direction LR
        F1["image_quality\npoor / fair"]
        F2["mismatch\nwrong object type"]
        F3["authenticity\nediting signals"]
        F4["user_history\nfraud · risk score · rejection rate"]
    end

    subgraph OUTPUT["Final Response — EvidenceReviewResult"]
        direction TB
        OUT1["verdict · confidence · severity\nissue_type · object_part · supporting_image_ids"]
        OUT2["risk_flags · justification\nreviewer_notes · processed_at"]
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
    R1 --> F1
    R2 --> F1
    R3 --> F1
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

## Risk Flag Categories

| Flag type | Severity | Trigger |
|---|---|---|
| `image_quality` | low / high | Image is poor or fair quality |
| `mismatch` | high | Image shows wrong object type |
| `authenticity` | high | Visual signs of editing or staging detected |
| `user_history` | medium / high | Prior fraud flags, elevated risk score, or >50% rejection rate |

> Risk flags run **after** verdict aggregation and **cannot** change the verdict. Informational only.

---

## Project Structure

```
evidence-review/
├── backend/
│   ├── app.py                  # FastAPI server — core pipeline
│   └── requirements.txt
├── frontend-node/              # React + Vite + Node.js frontend
│   ├── src/
│   │   ├── App.jsx             # Root with routing
│   │   ├── main.jsx
│   │   ├── components/
│   │   │   ├── Header.jsx
│   │   │   ├── ClaimForm.jsx       # Full sidebar form
│   │   │   ├── ConversationBuilder.jsx
│   │   │   ├── ImageUploader.jsx   # react-dropzone
│   │   │   ├── MermaidDiagram.jsx  # Live architecture diagram
│   │   │   └── ResultPanel.jsx     # Verdict display
│   │   ├── pages/
│   │   │   ├── ReviewPage.jsx
│   │   │   └── ArchitecturePage.jsx
│   │   └── utils/
│   │       ├── api.js              # axios client
│   │       └── helpers.js          # presets, base64 helpers
│   ├── package.json
│   └── vite.config.js              # proxies /api -> FastAPI :8000
├── sample_data/sample_claims.py
├── tests/test_api.py
├── sample_agent_output.json
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## Setup

### Backend (FastAPI + Python)

```bash
pip install -r backend/requirements.txt
export ANTHROPIC_API_KEY=your_key_here
uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

### Frontend (Node.js + React + Vite)

```bash
cd frontend-node
npm install
npm run dev        # http://localhost:3000
```

Vite proxies `/api` to `http://localhost:8000` automatically — no CORS config needed in dev.

### Production build

```bash
npm run build      # outputs to dist/
```

### Docker (full stack)

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
  "object_type": "car",
  "extracted_claim": "User claims rear bumper dent and paint scratches from parking lot collision.",
  "verdict": "SUPPORTED",
  "verdict_confidence": "high",
  "issue_type": "dent",
  "object_part": "rear bumper",
  "supporting_image_ids": ["IMG-001"],
  "risk_flags": [],
  "severity": "moderate",
  "justification": "Visual evidence supports the claim. [IMG-001] Clear dent visible on rear bumper with paint transfer.",
  "image_analysis_summary": "IMG-001: SUPPORTED | Dent on rear bumper (quality: good)",
  "evidence_sufficient": true,
  "reviewer_notes": "No additional reviewer notes.",
  "processed_at": "2024-01-15T10:31:04Z"
}
```

### POST /api/batch-review

Array of claim requests. Returns `{ results, errors, total }`.

---

## Supported Object Types

| Type | Example issues |
|---|---|
| `car` | dent, scratch, crack, broken glass, fire damage |
| `laptop` | broken_screen, bent chassis, water_damage, missing key |
| `package` | crushed, torn_packaging, missing seal, broken contents |

---

## Frontend (Node.js)

Built with React 18 + Vite + Tailwind CSS. Key packages:

| Package | Purpose |
|---|---|
| `react-dropzone` | Drag-and-drop image uploader |
| `mermaid@11` | Live architecture diagram rendering |
| `react-router-dom` | Two-tab navigation (Review / Architecture) |
| `axios` | API client with timeout and error handling |
| `react-hot-toast` | Verdict notifications |
| `lucide-react` | Icon set |

### Pages

- **`/`** — Claim Review: sidebar form + live verdict panel
- **`/architecture`** — Architecture: live Mermaid diagram + stage breakdown + decision logic

---

## Design Decisions

1. **Images are the source of truth.** User history risk scores produce flags only — never change the verdict.
2. **Contradiction overrides everything.** One contradicting image beats any number of supporting images.
3. **Two Claude calls per claim.** Text call for claim extraction (fast), then one Vision call per image.
4. **Structured JSON vision prompts.** Typed fields enforced — no free-text parsing in aggregation.
5. **Risk flags are post-verdict.** Strict separation of evidence vs. risk context.
