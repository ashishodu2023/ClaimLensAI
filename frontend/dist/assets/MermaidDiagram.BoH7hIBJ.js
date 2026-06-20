const __vite__mapDeps=(i,m=__vite__mapDeps,d=(m.f||(m.f=["assets/mermaid-vendor.DxZfShUZ.js","assets/react-vendor.CGrYMxWa.js"])))=>i.map(i=>d[i]);
import{_ as l}from"./mermaid-vendor.DxZfShUZ.js";import{j as s}from"./index.DQbqkej1.js";import{r as c}from"./react-vendor.CGrYMxWa.js";import"./ui-vendor.CpRna6Xq.js";const m=`
flowchart TD
    A([Claim Request<br/>claim_id · object_type · images · conversation · user_history])

    subgraph INGRESS["Input Validation"]
        direction TB
        V1{object_type valid?<br/>car · laptop · package}
        V2{images present?}
        V3{conversation not empty?}
    end

    subgraph EXTRACT["Step 1 — Claim Extraction"]
        E1[["Claude Sonnet Vision<br/>extract_claim_from_conversation()"]]
        E2(["Extracted claim sentence"])
    end

    subgraph VISION["Step 2 — Per-Image Vision Analysis"]
        direction LR
        IMG1[["Image 1<br/>analyze_image_with_vision()"]]
        IMG2[["Image 2<br/>analyze_image_with_vision()"]]
        IMGN[["Image N…"]]
        PERIMG(["Per-image JSON<br/>verdict · issue_type · object_part<br/>image_quality · authenticity"])
    end

    subgraph AGGREGATE["Step 3 — Verdict Aggregation"]
        direction TB
        AGG1{"Any image<br/>CONTRADICTED?"}
        AGG2{"SUPPORTED count<br/>≥ min_required?"}
        R1(["CONTRADICTED"])
        R2(["SUPPORTED"])
        R3(["INSUFFICIENT"])
    end

    subgraph FLAGS["Step 4 — Risk Flag Engine"]
        direction LR
        F1["Image quality<br/>poor / fair"]
        F2["Object mismatch<br/>wrong type in image"]
        F3["Authenticity<br/>editing signals"]
        F4["User history<br/>fraud · risk score · rejection rate"]
    end

    subgraph OUTPUT["Final Response — EvidenceReviewResult"]
        direction TB
        OUT1["verdict · confidence · severity<br/>issue_type · object_part<br/>supporting_image_ids"]
        OUT2["risk_flags · justification<br/>reviewer_notes · processed_at"]
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
`;function g(){const r=c.useRef(null);return c.useEffect(()=>{let a=!1;async function d(){const n=(await l(async()=>{const{default:t}=await import("./mermaid-vendor.DxZfShUZ.js").then(o=>o.a$);return{default:t}},__vite__mapDeps([0,1]))).default,e=window.matchMedia("(prefers-color-scheme: dark)").matches;if(n.initialize({startOnLoad:!1,theme:"base",fontFamily:"Inter, system-ui, sans-serif",themeVariables:{darkMode:e,fontSize:"13px",fontFamily:"Inter, system-ui, sans-serif",primaryColor:e?"#1e254a":"#EEEDFE",primaryTextColor:e?"#c5c0f5":"#26215C",primaryBorderColor:e?"#534AB7":"#AFA9EC",secondaryColor:e?"#0a2e1e":"#E1F5EE",secondaryTextColor:e?"#7dd4b4":"#04342C",secondaryBorderColor:e?"#0F6E56":"#5DCAA5",tertiaryColor:e?"#2d160a":"#FAECE7",tertiaryTextColor:e?"#f0a080":"#4A1B0C",tertiaryBorderColor:e?"#993C1D":"#D85A30",noteBkgColor:e?"#1a1a18":"#F1EFE8",noteTextColor:e?"#b0ae a6":"#2C2C2A",lineColor:e?"#6b7a99":"#888780",textColor:e?"#c2c0b6":"#3d3d3a",clusterBkg:e?"#0c1220":"#E6F1FB",clusterBorder:e?"#185FA5":"#378ADD",edgeLabelBackground:e?"#111520":"#ffffff"}}),!a&&r.current)try{const t=`mermaid-${Date.now()}`,{svg:o}=await n.render(t,m);if(!a&&r.current){r.current.innerHTML=o;const i=r.current.querySelector("svg");i&&(i.style.width="100%",i.style.height="auto",i.removeAttribute("height"))}}catch(t){!a&&r.current&&(r.current.innerHTML=`<p class="text-red-400 text-xs p-4">Diagram render error: ${t.message}</p>`)}}return d(),()=>{a=!0}},[]),s.jsx("div",{className:"w-full overflow-x-auto",children:s.jsx("div",{ref:r,className:"min-w-0 w-full"})})}export{g as default};
