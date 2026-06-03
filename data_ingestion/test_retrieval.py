import os

try:
    import google.generativeai as genai  # type: ignore
except Exception as e:
    raise RuntimeError("google-generativeai belum terinstall. Install dulu atau set EMBEDDING_PROVIDER=openai") from e

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = lambda: None

load_dotenv()

AWS_REGION = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "ap-southeast-1"
AWS_PROFILE = os.environ.get("AWS_PROFILE")

S3_VECTOR_BUCKET_NAME = os.environ.get("S3_VECTOR_BUCKET_NAME", "virtual-dealer-prod")
S3_VECTOR_INDEX_NAME = os.environ.get("S3_VECTOR_INDEX_NAME", "cars-index")
S3_VECTOR_DIMENSION = int(os.environ.get("S3_VECTOR_DIMENSION", "3072"))
S3_PAYLOAD_BUCKET_NAME = os.environ.get("S3_PAYLOAD_BUCKET_NAME", "virtual-dealer-cars-rag-prod")

GEMINI_EMBED_MODEL = os.environ.get("GEMINI_EMBED_MODEL", "models/gemini-embedding-2")
EMBEDDING_PROVIDER = os.environ.get("EMBEDDING_PROVIDER", "gemini").lower().strip()


def _embed_query_gemini(query: str) -> list:
    # from google import genai as genai_client

    # client = genai_client.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    resp = genai.embed_content(
        model=GEMINI_EMBED_MODEL,
        content=query,
        task_type="retrieval_document",
    )
    emb = resp.get("embedding") if isinstance(resp, dict) else getattr(resp, "embedding", None)
    if emb is None:
        raise RuntimeError("Embedding response empty")
    try:
        import numpy as np
        return np.asarray(emb, dtype=np.float32).tolist()
    except Exception:
        return [float(x) for x in emb]


def _get_s3vectors_client():
    import boto3

    aws_session = (
        boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
        if AWS_PROFILE
        else boto3.Session(region_name=AWS_REGION)
    )
    return aws_session.client("s3vectors", region_name=AWS_REGION)


def _get_s3_client():
    import boto3

    aws_session = (
        boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
        if AWS_PROFILE
        else boto3.Session(region_name=AWS_REGION)
    )
    return aws_session.client("s3")


def _fetch_text_from_s3(s3_client, text_key: str) -> str:
    try:
        response = s3_client.get_object(
            Bucket=S3_PAYLOAD_BUCKET_NAME,
            Key=text_key,
        )
        return response["Body"].read().decode("utf-8")
    except Exception as e:
        print(f"[WARN] Failed to fetch {text_key}: {e}")
        return ""


def retrieve(query: str, top_k: int = 5, filters: dict = None) -> list:
    vector = _embed_query_gemini(query)
    if len(vector) != S3_VECTOR_DIMENSION:
        raise RuntimeError(f"Embedding dimension mismatch: got {len(vector)} expected {S3_VECTOR_DIMENSION}")

    client = _get_s3vectors_client()

    req = {
        "vectorBucketName": S3_VECTOR_BUCKET_NAME,
        "indexName": S3_VECTOR_INDEX_NAME,
        "queryVector": {"float32": vector},
        "topK": top_k,
        "returnMetadata": True,
    }

    print(f"[DEBUG] Query vector dimension: {len(vector)}")
    print(f"[DEBUG] Request params: vectorBucketName={S3_VECTOR_BUCKET_NAME}, indexName={S3_VECTOR_INDEX_NAME}, topK={top_k}")

    resp = client.query_vectors(**req)

    vectors = resp.get("vectors") or []
    if not vectors:
        print(f"[DEBUG] Raw response keys: {list(resp.keys())}")
        print(f"[DEBUG] Full response: {resp}")

    s3_client = _get_s3_client()
    results = []
    for vec in vectors:
        distance = vec.get("distance", 0.0)
        key = vec.get("key", "")
        metadata = vec.get("metadata") or {}

        text_key = metadata.get("text_key", f"{key}.json")
        text = _fetch_text_from_s3(s3_client, text_key)

        results.append({
            "key": key,
            "distance": distance,
            "metadata": metadata,
            "text": text,
        })

    return results


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Test S3 Vector retrieval")
    parser.add_argument("query", nargs="?", default="gimana bagasi pajero")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    results = retrieve(args.query, top_k=args.top_k)

    print(f"\nQuery: {args.query}")
    print(f"Results: {len(results)}\n")
    print("-" * 80)

    for i, r in enumerate(results, 1):
        print(f"\n[Result {i}] Distance: {r['distance']:.4f}")
        print(f"Key: {r['key']}")
        print(f"Metadata: {r['metadata']}")
        text_preview = r['text']
        print(f"Text Preview: {text_preview}")
        print("-" * 80)


if __name__ == "__main__":
    main()