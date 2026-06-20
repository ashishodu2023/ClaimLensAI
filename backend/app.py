"""
ClaimLens — AI Damage Claim Intelligence — Production Backend
Scale target: millions of images/hour

Key optimizations:
  1. Fully async — all Claude calls use AsyncAnthropic, never block the event loop
  2. Parallel Vision analysis — all images in a claim analyzed concurrently (asyncio.gather)
  3. Claim extraction cached — same conversation text returns instantly on retry/duplicate
  4. Semaphore-based concurrency control — prevents API rate-limit spikes under burst load
  5. Exponential backoff retries — handles transient 529/rate-limit errors automatically
  6. orjson for JSON — 3-10× faster serialization/deserialization vs stdlib json
  7. Connection pooling — single AsyncAnthropic client reused across all requests (httpx pool)
  8. Structured concurrency — asyncio.gather with return_exceptions so one bad image
     never kills the entire claim
  9. Response caching layer — idempotent re-submissions return cached result immediately
 10. Graceful degradation — per-image errors produce INSUFFICIENT instead of 500
"""

import asyncio
import hashlib
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

import orjson
from anthropic import AsyncAnthropic, RateLimitError, APIStatusError
from cachetools import TTLCache
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, ORJSONResponse
from pydantic import BaseModel, field_validator
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

# ─── App bootstrap ────────────────────────────────────────────────────────────

app = FastAPI(
    title="ClaimLens — AI Damage Claim Intelligence",
    version="2.0.0",
    default_response_class=ORJSONResponse,  # faster JSON responses via orjson
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

# ─── Async Anthropic client (single shared instance = connection pool reuse) ──
_client: Optional[AsyncAnthropic] = None

def get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic(
            max_retries=0,   # we handle retries ourselves via tenacity
            timeout=60.0,
        )
    return _client

# ─── Concurrency control ──────────────────────────────────────────────────────
# Limit simultaneous in-flight Anthropic API calls.
# At 1 M images/hr ≈ 278/sec; tune MAX_CONCURRENT to your API tier's TPM limit.
MAX_CONCURRENT_API_CALLS = int(os.getenv("MAX_CONCURRENT_API_CALLS", "50"))
_api_semaphore: Optional[asyncio.Semaphore] = None

def get_semaphore() -> asyncio.Semaphore:
    global _api_semaphore
    if _api_semaphore is None:
        _api_semaphore = asyncio.Semaphore(MAX_CONCURRENT_API_CALLS)
    return _api_semaphore

# ─── In-process result cache (swap for Redis in multi-node prod) ──────────────
# TTL=300s, max 10k entries. Key = SHA-256 of canonical request JSON.
_result_cache: TTLCache = TTLCache(maxsize=10_000, ttl=300)

# Claim extraction cache — conversation text rarely changes between retries
_claim_cache: TTLCache = TTLCache(maxsize=50_000, ttl=600)

# ─── Models ───────────────────────────────────────────────────────────────────

ObjectType = Literal["car", "laptop", "package"]
Verdict     = Literal["SUPPORTED", "CONTRADICTED", "INSUFFICIENT"]
Severity    = Literal["minor", "moderate", "severe", "critical"]
Confidence  = Literal["high", "medium", "low"]
FlagSev     = Literal["low", "medium", "high"]
FlagType    = Literal["image_quality", "mismatch", "authenticity", "user_history"]


class ConversationTurn(BaseModel):
    role: Literal["user", "agent"]
    text: str


class UserHistory(BaseModel):
    previous_claims: int = 0
    approved_claims: int = 0
    rejected_claims: int = 0
    fraud_flags: int = 0
    account_age_days: int = 0
    risk_score: Optional[float] = None

    @field_validator("risk_score")
    @classmethod
    def clamp_risk(cls, v):
        if v is not None:
            return max(0.0, min(1.0, v))
        return v


class EvidenceImage(BaseModel):
    image_id: str
    base64_data: str
    media_type: Literal["image/jpeg", "image/png", "image/webp"] = "image/jpeg"

    @field_validator("base64_data")
    @classmethod
    def validate_b64(cls, v: str) -> str:
        # Strip data-URI prefix if accidentally included
        if "," in v:
            v = v.split(",", 1)[1]
        return v


class ClaimRequest(BaseModel):
    claim_id: str
    object_type: ObjectType
    conversation: list[ConversationTurn]
    images: list[EvidenceImage]
    user_history: Optional[UserHistory] = None
    minimum_evidence_required: int = 1

    @field_validator("images")
    @classmethod
    def at_least_one_image(cls, v):
        if not v:
            raise ValueError("At least one image is required")
        return v

    @field_validator("conversation")
    @classmethod
    def non_empty_conversation(cls, v):
        if not v:
            raise ValueError("Conversation cannot be empty")
        return v


class RiskFlag(BaseModel):
    flag_type: FlagType
    severity: FlagSev
    description: str


class EvidenceReviewResult(BaseModel):
    claim_id: str
    object_type: str
    extracted_claim: str
    verdict: Verdict
    verdict_confidence: Confidence
    issue_type: str
    object_part: str
    supporting_image_ids: list[str]
    risk_flags: list[RiskFlag]
    severity: Severity
    justification: str
    image_analysis_summary: str
    evidence_sufficient: bool
    reviewer_notes: str
    processed_at: str
    processing_ms: int          # latency telemetry
    chain_of_thought: str = ""  # agent reasoning across all images
    overrode_preliminary: bool = False  # True when agent disagreed with deterministic verdict
    override_reason: str = ""   # explanation when agent overrode


class BatchReviewResponse(BaseModel):
    results: list[EvidenceReviewResult]
    errors: list[dict]
    total: int
    succeeded: int
    failed: int
    processing_ms: int


# ─── Prompt builders ──────────────────────────────────────────────────────────

_VISION_PROMPT_TEMPLATE = """\
You are an expert insurance/logistics damage assessor analyzing visual evidence.

Object type: {object_type}
Image ID: {image_id}
Claimed damage: {extracted_claim}
{history_ctx}
Respond ONLY with a JSON object — no markdown, no code fences:

{{"image_id":"{image_id}","object_present":true/false,"object_type_matches":true/false,\
"damage_visible":true/false,"damage_description":"...","damage_matches_claim":true/false/null,\
"issue_type":"dent|scratch|crack|water_damage|fire_damage|missing_part|deformation|broken_screen|torn_packaging|crushed|other",\
"object_part":"specific part","image_quality":"good|fair|poor",\
"image_quality_issues":[],"authenticity_concerns":true/false,\
"authenticity_reason":"","severity":"minor|moderate|severe|critical",\
"verdict":"SUPPORTED|CONTRADICTED|INSUFFICIENT","confidence":"high|medium|low",\
"justification":"1-2 sentences grounded in what you see"}}

Rules:
- SUPPORTED: object clearly present, matching damage clearly visible.
- CONTRADICTED: object present in good condition where damage is claimed.
- INSUFFICIENT: object not visible, too dark/blurry, or damage not determinable.
- User history context is for risk flags ONLY — never changes the verdict.
"""

_HISTORY_CONTEXT = """\
User risk context (flag-only, does not affect verdict):
claims={previous}/{approved}approved/{rejected}rejected fraud_flags={fraud} \
account_age={age}d risk_score={risk}
"""

def _build_vision_prompt(
    object_type: str,
    extracted_claim: str,
    image_id: str,
    history: Optional[UserHistory],
) -> str:
    hctx = ""
    if history:
        hctx = _HISTORY_CONTEXT.format(
            previous=history.previous_claims,
            approved=history.approved_claims,
            rejected=history.rejected_claims,
            fraud=history.fraud_flags,
            age=history.account_age_days,
            risk=history.risk_score if history.risk_score is not None else "unknown",
        )
    return _VISION_PROMPT_TEMPLATE.format(
        object_type=object_type.upper(),
        image_id=image_id,
        extracted_claim=extracted_claim,
        history_ctx=hctx,
    )

# ─── Retry decorator for Anthropic calls ─────────────────────────────────────

def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, RateLimitError):
        return True
    if isinstance(exc, APIStatusError) and exc.status_code in (429, 529, 503, 502):
        return True
    return False

_anthropic_retry = retry(
    retry=retry_if_exception_type((RateLimitError, APIStatusError)),
    wait=wait_exponential(multiplier=1, min=1, max=30),
    stop=stop_after_attempt(5),
    reraise=True,
)

# ─── Core async functions ─────────────────────────────────────────────────────

def _conv_cache_key(conversation: list[ConversationTurn], object_type: str) -> str:
    text = object_type + "|" + "|".join(f"{t.role}:{t.text}" for t in conversation)
    return hashlib.sha256(text.encode()).hexdigest()


@_anthropic_retry
async def _extract_claim_async(
    conversation: list[ConversationTurn],
    object_type: str,
) -> str:
    """Extract damage claim from conversation. Results cached by content hash."""
    cache_key = _conv_cache_key(conversation, object_type)
    if cache_key in _claim_cache:
        return _claim_cache[cache_key]

    conv_text = "\n".join(f"{t.role.upper()}: {t.text}" for t in conversation)
    async with get_semaphore():
        resp = await get_client().messages.create(
            model="claude-sonnet-4-6",
            max_tokens=150,
            messages=[{
                "role": "user",
                "content": (
                    f"Extract the specific damage claim from this {object_type} conversation. "
                    "Return ONLY one concise sentence — no commentary.\n\n"
                    f"{conv_text}"
                ),
            }],
        )
    result = resp.content[0].text.strip()
    _claim_cache[cache_key] = result
    return result


_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)

def _parse_vision_json(raw: str, image_id: str) -> dict:
    """Parse Claude's vision response, stripping accidental code fences."""
    raw = raw.strip()
    m = _JSON_FENCE_RE.search(raw)
    if m:
        raw = m.group(1)
    try:
        return orjson.loads(raw)
    except Exception:
        # Fallback: return a safe INSUFFICIENT result instead of crashing
        return {
            "image_id": image_id,
            "object_present": False,
            "object_type_matches": False,
            "damage_visible": False,
            "damage_description": "Parse error — could not read model response",
            "damage_matches_claim": None,
            "issue_type": "other",
            "object_part": "unknown",
            "image_quality": "poor",
            "image_quality_issues": ["parse_error"],
            "authenticity_concerns": False,
            "authenticity_reason": "",
            "severity": "minor",
            "verdict": "INSUFFICIENT",
            "confidence": "low",
            "justification": "Model response could not be parsed.",
        }


@_anthropic_retry
async def _analyze_image_async(
    image: EvidenceImage,
    object_type: str,
    extracted_claim: str,
    history: Optional[UserHistory],
) -> dict:
    """Analyze one image. Runs concurrently with all other images in the claim."""
    prompt = _build_vision_prompt(object_type, extracted_claim, image.image_id, history)
    async with get_semaphore():
        resp = await get_client().messages.create(
            model="claude-sonnet-4-6",
            max_tokens=600,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": image.media_type,
                            "data": image.base64_data,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }],
        )
    return _parse_vision_json(resp.content[0].text, image.image_id)


async def _analyze_all_images(
    images: list[EvidenceImage],
    object_type: str,
    extracted_claim: str,
    history: Optional[UserHistory],
) -> list[dict]:
    """
    Analyze ALL images in parallel using asyncio.gather.
    return_exceptions=True means one failing image produces a degraded result
    instead of aborting the entire claim.
    """
    tasks = [
        _analyze_image_async(img, object_type, extracted_claim, history)
        for img in images
    ]
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    analyses = []
    for img, res in zip(images, raw_results):
        if isinstance(res, Exception):
            # Degrade gracefully: treat errored image as INSUFFICIENT
            analyses.append({
                "image_id": img.image_id,
                "object_present": False,
                "object_type_matches": True,
                "damage_visible": False,
                "damage_description": f"Analysis error: {type(res).__name__}",
                "issue_type": "other",
                "object_part": "unknown",
                "image_quality": "poor",
                "image_quality_issues": ["api_error"],
                "authenticity_concerns": False,
                "authenticity_reason": "",
                "severity": "minor",
                "verdict": "INSUFFICIENT",
                "confidence": "low",
                "justification": "Image could not be analyzed due to an API error.",
            })
        else:
            analyses.append(res)
    return analyses


# ─── Aggregation & flag logic (pure Python — no I/O) ─────────────────────────

_SEV_RANK = {"minor": 1, "moderate": 2, "severe": 3, "critical": 4}
_CONF_RANK = {"low": 1, "medium": 2, "high": 3}


def _aggregate(analyses: list[dict], min_required: int) -> dict:
    """
    Fast deterministic aggregation — used as the preliminary verdict
    that the Reasoning Agent can confirm or override.
    """
    verdicts  = [a.get("verdict") for a in analyses]
    supported = verdicts.count("SUPPORTED")
    contradicted = verdicts.count("CONTRADICTED")
    supporting_ids = [a["image_id"] for a in analyses if a.get("verdict") == "SUPPORTED"]

    if contradicted > 0:
        final_verdict, sufficient = "CONTRADICTED", True
    elif supported >= min_required:
        final_verdict, sufficient = "SUPPORTED", True
    else:
        final_verdict, sufficient = "INSUFFICIENT", False

    severities = [a.get("severity", "minor") for a in analyses if a.get("damage_visible")]
    best_sev   = max(severities, key=lambda s: _SEV_RANK.get(s, 0), default="minor")
    best_conf  = max(
        (a.get("confidence", "low") for a in analyses),
        key=lambda c: _CONF_RANK.get(c, 0),
    )
    primary = next((a for a in analyses if a.get("verdict") == "SUPPORTED"), analyses[0])
    return {
        "verdict": final_verdict,
        "verdict_confidence": best_conf,
        "supporting_image_ids": supporting_ids,
        "severity": best_sev,
        "evidence_sufficient": sufficient,
        "issue_type": primary.get("issue_type", "unknown"),
        "object_part": primary.get("object_part", "unknown"),
    }


# ─── Claim Reasoning Agent ────────────────────────────────────────────────────
# Elevates the system from a pipeline to a reasoning agent.
# Instead of counting verdicts deterministically, the agent:
#   1. Reviews ALL per-image analyses as a unified evidence set
#   2. Cross-references images (do photos show same or different damage areas?)
#   3. Weighs confidence, quality, and authenticity signals holistically
#   4. Produces a chain-of-thought explanation citing specific image IDs
#   5. Can OVERRIDE the preliminary verdict when evidence is ambiguous

_AGENT_SYSTEM_PROMPT = """You are a senior claims adjudicator with expertise in insurance fraud detection
and damage assessment. You receive structured per-image analyses from a vision
system and must produce a final, authoritative verdict on the claim.

Your job is to REASON across the full evidence set — not just count verdicts.
Consider:
- Do multiple images corroborate each other or tell conflicting stories?
- Is the claimed damage location consistent across all images?
- Does the damage pattern match the claimed incident type?
- Are authenticity or quality issues concentrated in certain images only?
- Does the preliminary verdict correctly weight all available evidence?

Images are the primary source of truth. User history is for risk flags ONLY.
A high-risk user with clear visual evidence must still receive SUPPORTED.
A low-risk user with contradicted visual evidence must still receive CONTRADICTED.

Respond ONLY with valid JSON — no markdown, no code fences, no preamble.
"""

_AGENT_USER_TEMPLATE = """CLAIM
=====
Object: {object_type}
Damage claimed: {extracted_claim}
Images submitted: {image_count}
Minimum evidence required: {min_required}

PRELIMINARY VERDICT (deterministic aggregation)
===============================================
{prelim_verdict} ({prelim_confidence} confidence)
Supporting: {prelim_supporting}

PER-IMAGE VISION ANALYSES
=========================
{analyses_text}

USER RISK CONTEXT (flags only — must NOT change verdict)
========================================================
{history_text}

Produce your final adjudication as JSON with these exact fields:
{{
  "verdict": "SUPPORTED|CONTRADICTED|INSUFFICIENT",
  "verdict_confidence": "high|medium|low",
  "severity": "minor|moderate|severe|critical",
  "issue_type": "dent|scratch|crack|water_damage|fire_damage|missing_part|deformation|broken_screen|torn_packaging|crushed|other",
  "object_part": "specific part affected",
  "supporting_image_ids": ["image IDs that support the verdict"],
  "chain_of_thought": "2-4 sentences explaining cross-image reasoning",
  "overrode_preliminary": true/false,
  "override_reason": "why preliminary verdict was wrong, or empty string"
}}
"""

def _fmt_analyses(analyses: list[dict]) -> str:
    lines = []
    for a in analyses:
        lines.append(
            f"[{a['image_id']}] verdict={a.get('verdict','?')} conf={a.get('confidence','?')}\n"
            f"  damage_visible={a.get('damage_visible','?')} quality={a.get('image_quality','?')}\n"
            f"  issue={a.get('issue_type','?')} part={a.get('object_part','?')} severity={a.get('severity','?')}\n"
            f"  auth_ok={not a.get('authenticity_concerns',False)}\n"
            f"  description: {a.get('damage_description','')}\n"
            f"  justification: {a.get('justification','')}\n"
        )
    return "\n".join(lines)

def _fmt_history(history) -> str:
    if not history:
        return "No user history provided."
    return (
        f"claims={history.previous_claims} approved={history.approved_claims} "
        f"rejected={history.rejected_claims} fraud_flags={history.fraud_flags} "
        f"risk_score={history.risk_score}"
    )

@_anthropic_retry
async def _reasoning_agent(
    analyses: list[dict],
    prelim: dict,
    extracted_claim: str,
    object_type: str,
    min_required: int,
    history,
) -> dict:
    """
    Reasoning Agent: one Claude call that thinks holistically across all
    image analyses and produces a final, explained verdict.
    Falls back to deterministic prelim verdict on any parsing error.
    """
    user_msg = _AGENT_USER_TEMPLATE.format(
        object_type=object_type.upper(),
        extracted_claim=extracted_claim,
        image_count=len(analyses),
        min_required=min_required,
        prelim_verdict=prelim["verdict"],
        prelim_confidence=prelim["verdict_confidence"],
        prelim_supporting=prelim["supporting_image_ids"],
        analyses_text=_fmt_analyses(analyses),
        history_text=_fmt_history(history),
    )

    async with get_semaphore():
        resp = await get_client().messages.create(
            model="claude-sonnet-4-6",
            max_tokens=600,
            system=_AGENT_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )

    raw = resp.content[0].text.strip()
    m = _JSON_FENCE_RE.search(raw)
    if m:
        raw = m.group(1)

    try:
        out = orjson.loads(raw)
    except Exception:
        # Unparseable — fall back silently to deterministic verdict
        return {**prelim,
                "chain_of_thought": "Reasoning agent response could not be parsed; using deterministic verdict.",
                "overrode_preliminary": False,
                "override_reason": ""}

    return {
        "verdict":              out.get("verdict",              prelim["verdict"]),
        "verdict_confidence":   out.get("verdict_confidence",   prelim["verdict_confidence"]),
        "severity":             out.get("severity",             prelim["severity"]),
        "issue_type":           out.get("issue_type",           prelim["issue_type"]),
        "object_part":          out.get("object_part",          prelim["object_part"]),
        "supporting_image_ids": out.get("supporting_image_ids", prelim["supporting_image_ids"]),
        "evidence_sufficient":  out.get("verdict") in ("SUPPORTED", "CONTRADICTED"),
        "chain_of_thought":     out.get("chain_of_thought", ""),
        "overrode_preliminary": out.get("overrode_preliminary", False),
        "override_reason":      out.get("override_reason", ""),
    }


def _build_flags(analyses: list[dict], history: Optional[UserHistory]) -> list[RiskFlag]:
    flags: list[RiskFlag] = []

    for a in analyses:
        quality = a.get("image_quality", "good")
        issues  = a.get("image_quality_issues") or []
        issue_str = ", ".join(issues) if issues else "unspecified"

        if quality == "poor":
            flags.append(RiskFlag(flag_type="image_quality", severity="high",
                description=f"Image {a['image_id']}: poor quality — {issue_str}"))
        elif quality == "fair":
            flags.append(RiskFlag(flag_type="image_quality", severity="low",
                description=f"Image {a['image_id']}: fair quality — {issue_str}"))

        if not a.get("object_type_matches", True):
            flags.append(RiskFlag(flag_type="mismatch", severity="high",
                description=f"Image {a['image_id']}: object does not match claimed type"))

        if a.get("authenticity_concerns"):
            flags.append(RiskFlag(flag_type="authenticity", severity="high",
                description=f"Image {a['image_id']}: {a.get('authenticity_reason') or 'authenticity concerns'}"))

    if history:
        if history.fraud_flags > 0:
            flags.append(RiskFlag(
                flag_type="user_history",
                severity="high" if history.fraud_flags >= 2 else "medium",
                description=f"User has {history.fraud_flags} prior fraud flag(s)",
            ))
        if history.risk_score is not None and history.risk_score > 0.7:
            flags.append(RiskFlag(flag_type="user_history", severity="high",
                description=f"Elevated risk score: {history.risk_score:.2f}"))
        if history.previous_claims >= 3:
            rate = history.rejected_claims / history.previous_claims
            if rate > 0.5:
                flags.append(RiskFlag(flag_type="user_history", severity="medium",
                    description=f"High rejection rate: {rate:.0%} ({history.rejected_claims}/{history.previous_claims})"))

    return flags


_VERDICT_PREAMBLE = {
    "SUPPORTED":     "Visual evidence supports the claim.",
    "CONTRADICTED":  "Visual evidence contradicts the claim.",
    "INSUFFICIENT":  "Insufficient visual evidence to verify or deny the claim.",
}


def _justification(analyses: list[dict], verdict: str) -> str:
    parts = [f"[{a['image_id']}] {a['justification']}"
             for a in analyses if a.get("justification")]
    body  = " | ".join(parts) or "No per-image justifications available."
    return f"{_VERDICT_PREAMBLE.get(verdict, '')} {body}"


def _summary(analyses: list[dict]) -> str:
    return "; ".join(
        f"{a['image_id']}: {a.get('verdict','?')} | {a.get('damage_description','')} (q:{a.get('image_quality','?')})"
        for a in analyses
    )


def _reviewer_notes(
    image_count: int,
    min_required: int,
    verdict: str,
    flags: list[RiskFlag],
) -> str:
    parts = []
    if image_count < min_required and verdict != "CONTRADICTED":
        parts.append(f"Only {image_count} image(s) submitted; {min_required} required.")
    high = sum(1 for f in flags if f.severity == "high")
    if high:
        parts.append(f"{high} high-severity flag(s) — manual review recommended.")
    return " ".join(parts) or "No additional reviewer notes."


# ─── Cache key for full claim ─────────────────────────────────────────────────

def _claim_cache_key(req: ClaimRequest) -> str:
    # Deterministic key based on content — safe to cache idempotent re-submissions
    payload = {
        "claim_id": req.claim_id,
        "object_type": req.object_type,
        "conv": [(t.role, t.text) for t in req.conversation],
        "imgs": [(i.image_id, i.base64_data[:32]) for i in req.images],  # prefix only for speed
        "min": req.minimum_evidence_required,
        "hist": req.user_history.model_dump() if req.user_history else None,
    }
    return hashlib.sha256(orjson.dumps(payload, option=orjson.OPT_SORT_KEYS)).hexdigest()


# ─── Core review pipeline ─────────────────────────────────────────────────────

async def _run_review(req: ClaimRequest) -> EvidenceReviewResult:
    t0 = time.monotonic()

    # Cache hit — return instantly
    cache_key = _claim_cache_key(req)
    if cache_key in _result_cache:
        return _result_cache[cache_key]

    # Step 1: Extract claim (cached separately by conversation hash)
    extracted_claim = await _extract_claim_async(req.conversation, req.object_type)

    # Step 2: Analyze all images IN PARALLEL
    analyses = await _analyze_all_images(
        req.images, req.object_type, extracted_claim, req.user_history
    )

    # Step 3: Deterministic preliminary verdict (fast, no API call)
    prelim = _aggregate(analyses, req.minimum_evidence_required)

    # Step 4: Reasoning Agent — cross-image holistic adjudication
    # Runs one additional Claude call that reasons across ALL image analyses
    # together, can override the deterministic verdict, and produces a
    # chain-of-thought explanation grounded in specific image observations.
    agg = await _reasoning_agent(
        analyses=analyses,
        prelim=prelim,
        extracted_claim=extracted_claim,
        object_type=req.object_type,
        min_required=req.minimum_evidence_required,
        history=req.user_history,
    )

    # Step 5: Risk flags and final assembly
    flags  = _build_flags(analyses, req.user_history)
    result = EvidenceReviewResult(
        claim_id=req.claim_id,
        object_type=req.object_type,
        extracted_claim=extracted_claim,
        verdict=agg["verdict"],
        verdict_confidence=agg["verdict_confidence"],
        issue_type=agg["issue_type"],
        object_part=agg["object_part"],
        supporting_image_ids=agg["supporting_image_ids"],
        risk_flags=flags,
        severity=agg["severity"],
        justification=_justification(analyses, agg["verdict"]),
        image_analysis_summary=_summary(analyses),
        evidence_sufficient=agg["evidence_sufficient"],
        reviewer_notes=_reviewer_notes(
            len(req.images), req.minimum_evidence_required, agg["verdict"], flags
        ),
        processed_at=datetime.now(timezone.utc).isoformat(),
        processing_ms=int((time.monotonic() - t0) * 1000),
        chain_of_thought=agg.get("chain_of_thought", ""),
        overrode_preliminary=agg.get("overrode_preliminary", False),
        override_reason=agg.get("override_reason", ""),
    )

    _result_cache[cache_key] = result
    return result


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health", response_class=ORJSONResponse)
async def health():
    return {
        "status": "ok",
        "service": "ClaimLens",
        "version": "2.0.0",
        "concurrency_limit": MAX_CONCURRENT_API_CALLS,
        "cache_size": len(_result_cache),
        "claim_cache_size": len(_claim_cache),
    }


@app.post("/api/review", response_model=EvidenceReviewResult, response_class=ORJSONResponse)
async def review_claim(req: ClaimRequest):
    """
    Single claim review.
    Validation is handled by Pydantic — invalid requests return 422 automatically.
    """
    try:
        return await _run_review(req)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Upstream API error: {exc}") from exc


@app.post("/api/batch-review", response_model=BatchReviewResponse, response_class=ORJSONResponse)
async def batch_review(reqs: list[ClaimRequest]):
    """
    Batch review — all claims processed concurrently.
    Individual failures do not abort the batch.
    """
    t0 = time.monotonic()
    tasks = [_run_review(r) for r in reqs]
    raw   = await asyncio.gather(*tasks, return_exceptions=True)

    results, errors = [], []
    for req, res in zip(reqs, raw):
        if isinstance(res, Exception):
            errors.append({"claim_id": req.claim_id, "error": str(res)})
        else:
            results.append(res)

    return BatchReviewResponse(
        results=results,
        errors=errors,
        total=len(reqs),
        succeeded=len(results),
        failed=len(errors),
        processing_ms=int((time.monotonic() - t0) * 1000),
    )


@app.get("/metrics", response_class=ORJSONResponse)
async def metrics():
    """Lightweight observability endpoint — scrape with Prometheus or Datadog."""
    sem = get_semaphore()
    return {
        "api_slots_available": sem._value,
        "api_slots_total": MAX_CONCURRENT_API_CALLS,
        "result_cache_hits": len(_result_cache),
        "claim_cache_entries": len(_claim_cache),
    }


# ─── Frontend static serving ──────────────────────────────────────────────────

@app.get("/")
async def serve_frontend():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/{path:path}")
async def serve_static(path: str):
    fp = FRONTEND_DIR / path
    if fp.exists() and fp.is_file():
        return FileResponse(fp)
    return FileResponse(FRONTEND_DIR / "index.html")
