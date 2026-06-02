import argparse
import json
import os
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import boto3
try:
    import numpy as np  # type: ignore
except Exception:
    np = None

try:
    from dotenv import load_dotenv  # type: ignore
except Exception:
    load_dotenv = lambda: None

load_dotenv()

AWS_REGION = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "ap-southeast-1"
AWS_PROFILE = os.environ.get("AWS_PROFILE")

S3_VECTOR_BUCKET_NAME = os.environ.get("S3_VECTOR_BUCKET_NAME", "virtual-dealer-prod")
S3_VECTOR_INDEX_NAME = os.environ.get("S3_VECTOR_INDEX_NAME", "cars-index")
S3_VECTOR_DIMENSION = int(os.environ.get("S3_VECTOR_DIMENSION", "3072"))
S3_VECTOR_METADATA_MAX_BYTES = int(os.environ.get("S3_VECTOR_METADATA_MAX_BYTES", "2048"))
S3_VECTOR_TEXT_PREVIEW_CHARS = int(os.environ.get("S3_VECTOR_TEXT_PREVIEW_CHARS", "400"))
S3_PAYLOAD_BUCKET_NAME = os.environ.get("S3_PAYLOAD_BUCKET_NAME", "virtual-dealer-cars-rag-prod")

GEMINI_EMBED_MODEL = os.environ.get("GEMINI_EMBED_MODEL", "models/gemini-embedding-2")
OPENAI_EMBED_MODEL = os.environ.get("OPENAI_EMBED_MODEL", "text-embedding-3-small")
OPENAI_EMBED_ENDPOINT = os.environ.get("OPENAI_EMBED_ENDPOINT", "")
OPENAI_EMBED_API_KEY = os.environ.get("OPENAI_EMBED_API_KEY", "")


# MODEL_ENDPOINT = "http://localhost:20128/v1"
# MODEL_API_KEY = "sk-d89117e5f05a4ffa-djnjno-ecc582ac"
# MODEL_ID = "vx/gemini-3.1-pro-preview"

OPENAI_CHAT_ENDPOINT = os.environ.get("OPENAI_CHAT_ENDPOINT") or os.environ.get("MODEL_ENDPOINT") or ""
OPENAI_CHAT_API_KEY = (
    os.environ.get("OPENAI_CHAT_API_KEY")
    or os.environ.get("MODEL_API_KEY")
    or os.environ.get("ANTHROPIC_API_KEY")
    or ""
)
OPENAI_CHAT_MODEL = os.environ.get("OPENAI_CHAT_MODEL") or os.environ.get("MODEL_ID") or ""

EMBEDDING_PROVIDER = os.environ.get("EMBEDDING_PROVIDER", "gemini").lower().strip()
USE_LLM_EXTRACT = os.environ.get("USE_LLM_EXTRACT", "1").strip() not in {"0", "false", "no"}

PROJECT_ROOT = Path(__file__).resolve().parent
OCR_DIR = Path(os.environ.get("OCR_DIR") or (PROJECT_ROOT / "src" / "ocr_results")).resolve()
SUMMARY_JSON_PATH = Path(os.environ.get("SUMMARY_JSON_PATH") or (PROJECT_ROOT / "src" / "hasil_summary.json")).resolve()
KONTAK_JSON_PATH = Path(os.environ.get("KONTAK_JSON_PATH") or (PROJECT_ROOT / "src" / "kontak.json")).resolve()


@dataclass
class VectorChunk:
    key: str
    vector: Optional[List[float]]
    metadata: Dict[str, Any]
    payload: Dict[str, Any]


def _slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value


def _clean_md(text: str) -> str:
    lines: List[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if re.fullmatch(r"[\W\d_]+", line):
            continue
        lines.append(raw.rstrip())
    return "\n".join(lines).strip()


def _parse_car_from_markdown(md_text: str, file_stem: str) -> Dict[str, Any]:
    title_line = ""
    for line in md_text.splitlines():
        if line.lstrip().startswith("#"):
            title_line = line.lstrip("#").strip()
            break

    title = title_line or file_stem
    year_match = re.search(r"\b(20\d{2})\b", title) or re.search(r"\b(20\d{2})\b", "\n".join(md_text.splitlines()[:60]))
    year: Optional[int] = int(year_match.group(1)) if year_match else None

    upper_title = title.upper()
    upper_head = "\n".join(md_text.splitlines()[:40]).upper()
    brand = None
    model = None

    if "MITSUBISHI" in upper_title or "MITSUBISHI" in upper_head:
        brand = "Mitsubishi"
        m = re.search(r"-\s*([A-Z0-9 \-]+)$", upper_title)
        if m:
            model = m.group(1).strip()
        else:
            model = upper_title.replace("MITSUBISHI", "").replace("MOTORS", "").strip(" -")
    else:
        parts = re.split(r"\s*-\s*", title, maxsplit=1)
        if len(parts) == 2:
            brand = parts[0].strip().title()
            model = parts[1].strip()
        else:
            model = title.strip()

    model = re.sub(r"\s{2,}", " ", (model or file_stem)).strip()
    model_title = model.title()
    model_slug = _slugify(model_title)
    car_id = f"{model_slug}-{year}" if year else model_slug

    return {
        "car_id": car_id,
        "brand": brand,
        "model": model_title,
        "year": year,
        "model_slug": model_slug,
        "title": title,
    }


def _split_markdown_sections(md_text: str) -> Dict[str, str]:
    md_text = _clean_md(md_text)
    spec_match = re.search(r"(?im)^##\s+.*(?:specification|spesifikasi)\b.*$", md_text)
    if not spec_match:
        return {"fitur": md_text, "spesifikasi_teknis": ""}

    after_spec = md_text[spec_match.start() :]
    fitur_after_match = re.search(r"(?im)^(##|###)\s+.*(?:fitur|features|color options)\b.*$", after_spec)

    if not fitur_after_match:
        fitur_part = md_text[: spec_match.start()].strip()
        spec_part = md_text[spec_match.start() :].strip()
        return {"fitur": fitur_part, "spesifikasi_teknis": spec_part}

    split_at = spec_match.start() + fitur_after_match.start()
    fitur_part = (md_text[: spec_match.start()] + "\n\n" + md_text[split_at:]).strip()
    spec_part = md_text[spec_match.start() : split_at].strip()
    return {"fitur": fitur_part, "spesifikasi_teknis": spec_part}


def _load_markdown_sources(use_llm_extract: bool) -> Dict[str, Dict[str, Any]]:
    cars: Dict[str, Dict[str, Any]] = {}
    for path in sorted(OCR_DIR.glob("*.md")):
        md_text = path.read_text(encoding="utf-8", errors="ignore")
        meta = _parse_car_from_markdown(md_text, path.stem)
        if use_llm_extract:
            extracted = _extract_sections_with_llm(md_text)
            sections = {
                "spesifikasi_teknis": extracted.get("spesifikasi_teknis", ""),
                "fitur": extracted.get("fitur", ""),
            }
            meta["kontak_fallback"] = extracted.get("kontak", "")
        else:
            sections = _split_markdown_sections(md_text)
        car_id = meta["car_id"]
        cars[car_id] = {**meta, **sections, "source_path": str(path)}
    return cars


def _load_summary_sources() -> List[Dict[str, Any]]:
    if not SUMMARY_JSON_PATH.exists():
        return []
    return json.loads(SUMMARY_JSON_PATH.read_text(encoding="utf-8"))


def _extract_kontak_from_markdown(md_text: str, default_dealer_name: str) -> Dict[str, Any]:
    head = "\n".join(md_text.splitlines()[:80])
    phone_matches = re.findall(r"(?:\+62|62|0)\d[\d\-\s]{7,}\d", head)
    website_match = re.search(r"(https?://[^\s)]+|www\.[^\s)]+)", head, flags=re.I)

    kontak: Dict[str, Any] = {"dealer_name": default_dealer_name}
    if phone_matches:
        kontak["phone"] = phone_matches[0].replace(" ", "")
    if website_match:
        kontak["website"] = website_match.group(1)
    return {k: v for k, v in kontak.items() if v}


def _load_kontak_sources(cars: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    if KONTAK_JSON_PATH.exists():
        data = json.loads(KONTAK_JSON_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
        if isinstance(data, list):
            out: Dict[str, Dict[str, Any]] = {}
            for item in data:
                if isinstance(item, dict) and item.get("car_id"):
                    out[item["car_id"]] = item
            return out
        return {}

    out: Dict[str, Dict[str, Any]] = {}
    for car_id, meta in cars.items():
        src = meta.get("source_path")
        if not src:
            continue
        md_text = Path(src).read_text(encoding="utf-8", errors="ignore")
        dealer_name = f"{meta.get('brand') or ''} Customer Care".strip() or "Customer Care"
        kontak = _extract_kontak_from_markdown(md_text, dealer_name)
        if kontak:
            out[car_id] = kontak
    return out


def _match_summary_item_to_car_id(item: Dict[str, Any], cars: Dict[str, Dict[str, Any]]) -> str:
    fname = str(item.get("file_name") or "")
    stem = Path(fname).stem.lower()
    stem = re.sub(r"(?:_?transcript|_?summary)$", "", stem)
    stem = stem.replace(" ", "-")
    stem = re.sub(r"-{2,}", "-", stem).strip("-")

    for car_id, meta in cars.items():
        model_slug = str(meta.get("model_slug") or "")
        if model_slug and model_slug in stem:
            return car_id
    return _slugify(stem) or "unknown"


def _kontak_to_text(kontak: Dict[str, Any]) -> str:
    parts: List[str] = []
    for key in ["dealer_name", "phone", "whatsapp", "address", "email", "website", "notes"]:
        val = kontak.get(key)
        if val:
            parts.append(f"{key}: {val}")
    return "\n".join(parts).strip()


def _truncate_str(s: str, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    if len(s) <= max_chars:
        return s
    if max_chars == 1:
        return "…"
    return s[: max_chars - 1] + "…"


def _metadata_size_bytes(metadata: Dict[str, Any]) -> int:
    return len(json.dumps(metadata, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def _sanitize_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    cleaned: Dict[str, Any] = {}
    for k, v in metadata.items():
        if v is None:
            continue
        if isinstance(v, str):
            sv = v.strip()
            if not sv:
                continue
            cleaned[k] = _truncate_str(sv, 512)
            continue
        cleaned[k] = v

    if _metadata_size_bytes(cleaned) <= S3_VECTOR_METADATA_MAX_BYTES:
        return cleaned

    drop_order = [
        "address",
        "notes",
        "website",
        "email",
        "whatsapp",
        "phone",
        "model",
        "brand",
        "year",
        "text_preview",
    ]
    for k in drop_order:
        if k in cleaned and _metadata_size_bytes(cleaned) > S3_VECTOR_METADATA_MAX_BYTES:
            cleaned.pop(k, None)

    if _metadata_size_bytes(cleaned) <= S3_VECTOR_METADATA_MAX_BYTES:
        return cleaned

    for cap in [256, 128, 64, 32]:
        for k, v in list(cleaned.items()):
            if isinstance(v, str):
                cleaned[k] = _truncate_str(v, cap)
        if _metadata_size_bytes(cleaned) <= S3_VECTOR_METADATA_MAX_BYTES:
            return cleaned

    essential = {k: v for k, v in cleaned.items() if k in {"car_id", "field_name", "field"}}
    return essential if essential else {"car_id": cleaned.get("car_id", "unknown")}


def _iter_chunks(
    cars: Dict[str, Dict[str, Any]],
    summaries: List[Dict[str, Any]],
    kontaks: Dict[str, Dict[str, Any]],
) -> List[VectorChunk]:
    merged: Dict[str, Dict[str, Any]] = {car_id: dict(meta) for car_id, meta in cars.items()}

    for item in summaries:
        car_id = _match_summary_item_to_car_id(item, cars)
        merged.setdefault(car_id, {"car_id": car_id})
        for field in ["pros", "cons", "driving_experience", "highlighted_features", "overall_conclusion"]:
            val = item.get(field)
            if isinstance(val, str) and val.strip():
                merged[car_id][field] = val.strip()

    for car_id, kontak in kontaks.items():
        merged.setdefault(car_id, {"car_id": car_id})
        merged[car_id]["kontak_raw"] = kontak

    chunks: List[VectorChunk] = []
    target_fields = [
        "spesifikasi_teknis",
        "fitur",
        "kontak",
        "pros",
        "cons",
        "driving_experience",
        "highlighted_features",
        "overall_conclusion",
    ]

    for car_id, meta in merged.items():
        brand = meta.get("brand")
        model = meta.get("model")
        year = meta.get("year")

        for field in target_fields:
            if field == "kontak":
                kontak_raw = meta.get("kontak_raw") or {}
                if (not kontak_raw) and meta.get("kontak_fallback"):
                    kontak_raw = {"dealer_name": f"{brand or ''} Customer Care".strip() or "Customer Care", "notes": meta.get("kontak_fallback")}
                if not isinstance(kontak_raw, dict) or not kontak_raw:
                    continue
                text = _kontak_to_text(kontak_raw)
                metadata: Dict[str, Any] = _sanitize_metadata({
                    "car_id": car_id,
                    "brand": brand,
                    "model": model,
                    "field": field,
                })
                chunks.append(
                    VectorChunk(
                        key=f"{car_id}_{field}",
                        vector=None,
                        metadata=metadata,
                        payload={"text": text},
                    )
                )
                continue

            text = meta.get(field)
            if not isinstance(text, str) or not text.strip():
                continue
            metadata = _sanitize_metadata({
                "car_id": car_id,
                "brand": brand,
                "model": model,
                "year": year,
                "field": field,
            })
            chunks.append(
                VectorChunk(
                    key=f"{car_id}_{field}",
                    vector=None,
                    metadata=metadata,
                    payload={"text": text.strip()},
                )
            )

    return chunks


def _embed_text(text: str, retries: int = 3) -> List[float]:
    if EMBEDDING_PROVIDER == "openai":
        return _embed_text_openai(text, retries=retries)
    return _embed_text_gemini(text, retries=retries)


def _embed_text_gemini(text: str, retries: int = 3) -> List[float]:
    try:
        import google.generativeai as genai  # type: ignore
    except Exception as e:
        raise RuntimeError("google-generativeai belum terinstall. Install dulu atau set EMBEDDING_PROVIDER=openai") from e

    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
    last_err: Optional[Exception] = None
    for i in range(retries):
        try:
            resp = genai.embed_content(
                model=GEMINI_EMBED_MODEL,
                content=text,
                task_type="retrieval_document",
            )
            emb = resp.get("embedding") if isinstance(resp, dict) else getattr(resp, "embedding", None)
            if not emb:
                raise RuntimeError("Embedding response empty")
            if np is not None:
                return np.asarray(emb, dtype=np.float32).tolist()
            return [float(x) for x in emb]
        except Exception as e:
            last_err = e
            print(f"Error generating embedding: {e}")
            time.sleep(1.5 * (i + 1))
    if last_err:
        print(f"Error generating embedding: {last_err}")
    return []


def _embed_text_openai(text: str, retries: int = 3) -> List[float]:
    try:
        from openai import OpenAI  # type: ignore
    except Exception as e:
        raise RuntimeError("openai belum terinstall. Install dulu atau set EMBEDDING_PROVIDER=gemini") from e

    endpoint = OPENAI_EMBED_ENDPOINT or OPENAI_CHAT_ENDPOINT
    api_key = OPENAI_EMBED_API_KEY or OPENAI_CHAT_API_KEY
    if not endpoint or not api_key:
        raise RuntimeError("OPENAI_EMBED_ENDPOINT/OPENAI_EMBED_API_KEY belum diset (atau pakai OPENAI_CHAT_ENDPOINT/OPENAI_CHAT_API_KEY)")

    oai = OpenAI(base_url=endpoint, api_key=api_key)
    last_err: Optional[Exception] = None
    for i in range(retries):
        try:
            resp = oai.embeddings.create(model=OPENAI_EMBED_MODEL, input=text)
            emb = resp.data[0].embedding
            if np is not None:
                return np.asarray(emb, dtype=np.float32).tolist()
            return [float(x) for x in emb]
        except Exception as e:
            last_err = e
            time.sleep(1.5 * (i + 1))
    raise last_err or RuntimeError("Embedding failed")


def _extract_sections_with_llm(markdown_content: str, retries: int = 2) -> Dict[str, str]:
    try:
        from openai import OpenAI  # type: ignore
    except Exception as e:
        raise RuntimeError("openai belum terinstall untuk LLM extract. Install openai atau set USE_LLM_EXTRACT=0") from e

    if not OPENAI_CHAT_ENDPOINT or not OPENAI_CHAT_API_KEY or not OPENAI_CHAT_MODEL:
        raise RuntimeError("OPENAI_CHAT_ENDPOINT/OPENAI_CHAT_API_KEY/OPENAI_CHAT_MODEL (atau MODEL_ENDPOINT/MODEL_API_KEY/MODEL_ID) belum diset untuk LLM extract")

    oai = OpenAI(base_url=OPENAI_CHAT_ENDPOINT, api_key=OPENAI_CHAT_API_KEY)
    last_err: Optional[Exception] = None
    for i in range(retries):
        try:
            completion = oai.chat.completions.create(
                model=OPENAI_CHAT_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "Extract the car details into JSON with keys: spesifikasi_teknis, fitur, kontak. Return ONLY a valid JSON object without markdown/code blocks.",
                    },
                    {"role": "user", "content": markdown_content},
                ],
                temperature=0.2,
            )
            response_text = (completion.choices[0].message.content or "").strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            data = json.loads(response_text.strip())
            out: Dict[str, str] = {}
            for k in ["spesifikasi_teknis", "fitur", "kontak"]:
                v = data.get(k, "")
                if isinstance(v, (dict, list)):
                    out[k] = json.dumps(v, ensure_ascii=False)
                else:
                    out[k] = str(v or "").strip()
            return out
        except Exception as e:
            last_err = e
            time.sleep(1.5 * (i + 1))

    sections = _split_markdown_sections(markdown_content)
    kontak = _extract_kontak_from_markdown(markdown_content, "Customer Care")
    kontak_text = _kontak_to_text(kontak) if kontak else ""
    return {
        "spesifikasi_teknis": sections.get("spesifikasi_teknis", ""),
        "fitur": sections.get("fitur", ""),
        "kontak": kontak_text,
    }


def _batch(items: List[Any], size: int) -> Iterable[List[Any]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _get_s3vectors_client():
    aws_session = (
        boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
        if AWS_PROFILE
        else boto3.Session(region_name=AWS_REGION)
    )
    return aws_session.client("s3vectors", region_name=AWS_REGION)


def _get_s3_client():
    aws_session = (
        boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
        if AWS_PROFILE
        else boto3.Session(region_name=AWS_REGION)
    )
    return aws_session.client("s3")


def _upload_text_payload(s3_client, chunks: List[VectorChunk]) -> None:
    for c in chunks:
        text = str(c.payload.get("text") or "")
        if not text:
            continue
        key = f"{c.key}.json"
        s3_client.put_object(
            Bucket=S3_PAYLOAD_BUCKET_NAME,
            Key=key,
            Body=text.encode("utf-8"),
            ContentType="application/json",
        )


def _clear_all_vectors(s3vectors_client) -> int:
    deleted = 0
    next_token: Optional[str] = None
    while True:
        req: Dict[str, Any] = {
            "vectorBucketName": S3_VECTOR_BUCKET_NAME,
            "indexName": S3_VECTOR_INDEX_NAME,
            "maxResults": 500,
        }
        if next_token:
            req["nextToken"] = next_token
        resp = s3vectors_client.list_vectors(**req)
        vectors = resp.get("vectors") or []
        keys = [v.get("key") for v in vectors if v.get("key")]
        for key_batch in _batch(keys, 500):
            s3vectors_client.delete_vectors(
                vectorBucketName=S3_VECTOR_BUCKET_NAME,
                indexName=S3_VECTOR_INDEX_NAME,
                keys=key_batch,
            )
            deleted += len(key_batch)
        next_token = resp.get("nextToken")
        if not next_token:
            break
    return deleted


def _upsert_chunks(s3vectors_client, chunks: List[VectorChunk], batch_size: int = 25) -> None:
    for chunk_batch in _batch(chunks, batch_size):
        vectors = []
        for c in chunk_batch:
            if not c.vector:
                continue
            metadata = dict(c.metadata)
            metadata["text_key"] = f"{c.key}.json"
            vectors.append(
                {
                    "key": c.key,
                    "data": {"float32": c.vector},
                    "metadata": metadata,
                }
            )
        if not vectors:
            continue
        s3vectors_client.put_vectors(
            vectorBucketName=S3_VECTOR_BUCKET_NAME,
            indexName=S3_VECTOR_INDEX_NAME,
            vectors=vectors,
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-clear", action="store_true")
    parser.add_argument("--no-llm-extract", action="store_true")
    parser.add_argument("--output", default="")
    parser.add_argument("--batch-size", type=int, default=int(os.environ.get("S3V_BATCH_SIZE", "25")))
    args = parser.parse_args()

    use_llm_extract = USE_LLM_EXTRACT and (not args.no_llm_extract) and (not args.dry_run)
    cars = _load_markdown_sources(use_llm_extract)
    summaries = _load_summary_sources()
    kontaks = _load_kontak_sources(cars)
    chunks = _iter_chunks(cars, summaries, kontaks)

    if args.dry_run:
        print(f"DRY_RUN chunks={len(chunks)} cars={len({c.metadata.get('car_id') for c in chunks})}")
        for c in chunks:
            print(f"- {c.key} ({c.metadata.get('field')}) len(text)={len(str(c.payload.get('text') or ''))}")
        if args.output:
            Path(args.output).write_text(
                json.dumps([{k: v for k, v in asdict(c).items() if k != "vector"} for c in chunks], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        return

    for c in chunks:
        if c.vector is None:
            c.vector = _embed_text(str(c.payload.get("text") or ""))
            if c.vector and len(c.vector) != S3_VECTOR_DIMENSION:
                raise RuntimeError(
                    f"Embedding dimension mismatch for {c.key}: got {len(c.vector)} expected {S3_VECTOR_DIMENSION}"
                )

    if args.output:
        Path(args.output).write_text(
            json.dumps([asdict(c) for c in chunks], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    s3vectors_client = _get_s3vectors_client()

    if not args.no_clear:
        deleted = _clear_all_vectors(s3vectors_client)
        print(f"Cleared vectors: {deleted}")

    s3_client = _get_s3_client()
    _upload_text_payload(s3_client, chunks)
    print(f"Uploaded text payloads to S3: {len(chunks)}")

    _upsert_chunks(s3vectors_client, chunks, batch_size=args.batch_size)
    print(f"Upserted chunks: {len(chunks)}")


if __name__ == "__main__":
    main()
