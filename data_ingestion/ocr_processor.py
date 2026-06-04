from google.cloud import documentai_v1 as documentai
from pathlib import Path
from google import genai
import os

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "./shekinah-489217-c432caac7134.json"

project_id = "..."
location = "..."
processor_id = "..."


GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
client = documentai.DocumentProcessorServiceClient()
gemini = genai.Client(api_key=GEMINI_API_KEY)
name = f"projects/{project_id}/locations/{location}/processors/{processor_id}"


def ocr_pdf(file_path):
    with open(file_path, "rb") as f:
        content = f.read()

    raw_document = documentai.RawDocument(
        content=content,
        mime_type="application/pdf"
    )
    request = documentai.ProcessRequest(name=name, raw_document=raw_document)
    result = client.process_document(request=request)
    return result.document.text


def cleanup_with_gemini(raw_text, filename=""):
    prompt = f"""Berikut adalah hasil OCR dari dokumen PDF bernama "{filename}".
Teks ini mungkin berantakan karena proses OCR.

Tugasmu:
1. Rapikan teks menjadi Markdown yang bersih dan terstruktur
2. Identifikasi dan pisahkan tiap section menggunakan heading Markdown (##, ###, dst.)
3. Pertahankan semua konten asli — jangan tambah atau hilangkan informasi
4. Perbaiki typo yang jelas akibat OCR (misalnya "rn" yang seharusnya "m")
5. Format tabel, list, atau data terstruktur jika ada

Hasil OCR:
{raw_text}

Kembalikan HANYA teks Markdown, tanpa penjelasan tambahan."""

    response = gemini.models.generate_content(
        model="gemini-3.1-pro-preview",
        contents=prompt,
    )
    return response.text


def ocr_folder(folder_path, output_folder=None):
    folder = Path(folder_path)
    pdf_files = sorted(folder.glob("*.pdf"))

    if not pdf_files:
        print(f"Tidak ada PDF di {folder_path}")
        return {}

    output_folder = Path("./src/ocr_results/")
    output_folder.mkdir(exist_ok=True)

    results = {}

    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"[{i}/{len(pdf_files)}] {pdf_path.name}")

        try:
            # Step 1: OCR
            print(f"  → OCR ...", end=" ", flush=True)
            raw_text = ocr_pdf(pdf_path)
            print(f"✓ ({len(raw_text)} karakter)")

            # Step 2: Cleanup via Gemini
            print(f"  → Rapikan dengan Gemini ...", end=" ", flush=True)
            markdown_text = cleanup_with_gemini(raw_text, filename=pdf_path.name)
            print(f"✓ ({len(markdown_text)} karakter)")

            results[pdf_path.name] = markdown_text

            # Simpan sebagai .md
            output_path = output_folder / (pdf_path.stem + ".md")
            output_path.write_text(markdown_text, encoding="utf-8")

        except Exception as e:
            print(f"  ✗ Error: {e}")
            results[pdf_path.name] = None

    sukses = sum(v is not None for v in results.values())
    print(f"\nSelesai! {sukses}/{len(pdf_files)} berhasil.")
    print(f"Hasil disimpan di: {output_folder}")
    return results


# --- Jalankan ---
results = ocr_folder("./src/brocure/")
