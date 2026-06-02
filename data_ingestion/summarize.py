import os
import json
from openai import OpenAI
from anthropic import Anthropic

from dotenv import load_dotenv
load_dotenv()
# from openai import OpenAI  # Uncomment jika ingin menggunakan OpenAI API

MODEL_ENDPOINT = os.environ.get("MODEL_ENDPOINT", "https://ai.bluepack.my.id/anthropic")
MODEL_API_KEY = os.environ.get("MODEL_API_KEY") or os.environ.get("ANTHROPIC_API_KEY") or ""
MODEL_ID = os.environ.get("MODEL_ID", "claude-sonnet-4.6")

client = Anthropic(
    base_url=MODEL_ENDPOINT,
    api_key=MODEL_API_KEY
)

print(MODEL_ENDPOINT)
def summarize_text(text):
    """
    Fungsi untuk mengekstrak testimoni dari teks transcript menggunakan LLM.
    """
    
    # Prompt khusus untuk mengekstrak testimoni mobil
    system_prompt = """
    You are an automotive expert assistant. Your task is to analyze YouTube video transcripts and extract user testimonials or reviews regarding the car being discussed.
    
    Please create a structured summary in JSON format with the following fields:
    {
        "pros": "What are the positive aspects experienced by the user?",
        "cons": "What are the complaints or negative aspects experienced by the user?",
        "driving_experience": "How is the comfort, engine performance, and handling of the car?",
        "highlighted_features": "Which features are most discussed, praised, or criticized?",
        "overall_conclusion": "Is the user generally satisfied or not?"
    }
    
    ### Rules
    - Ignore off-topic conversations such as intros, outros, calls to subscribe, or sponsorships. Focus purely on the car testimonial.
    - Return ONLY the JSON object, do not add any additional text or explanations.
    - All content in Bahasa Indonesia.
    """

    response = client.messages.create(
        model=MODEL_ID,
        system=system_prompt,
        messages=[
            {"role": "user", "content": f"Here's the transcription:\n\n{text}"}
        ],
        max_tokens=2048
    )
    print(response)
    
    text_block = None
    for block in response.content:
        if hasattr(block, 'type') and block.type == 'text':
            text_block = block
            break
    
    if text_block is None:
        return {"error": "No text block found in response"}
    
    json_text = text_block.text.strip()
    if json_text.startswith("```json"):
        json_text = json_text[7:]
    if json_text.startswith("```"):
        json_text = json_text[3:]
    if json_text.endswith("```"):
        json_text = json_text[:-3]
    json_text = json_text.strip()
    
    result = json.loads(json_text)
    return result
    
input_folder = "./src/transcripts"
output_json = "./src/hasil_summary.json"

hasil_akhir = []

# Membaca semua file .txt di dalam folder transcripts
for filename in os.listdir(input_folder):
    if filename.endswith(".txt"):
        filepath = os.path.join(input_folder, filename)
        
        print(f"Sedang merangkum: {filename}...")
        
        # Baca isi file transcript
        with open(filepath, "r", encoding="utf-8") as f:
            transcript_text = f.read()
        
        # Proses rangkuman
        summary = summarize_text(transcript_text)
        
        # Masukkan ke dalam list
        hasil_akhir.append({
            "file_name": filename,
            "pros": summary.get("pros", ""),
            "cons": summary.get("cons", ""),
            "driving_experience": summary.get("driving_experience", ""),
            "highlighted_features": summary.get("highlighted_features", ""),
            "overall_conclusion": summary.get("overall_conclusion", "")
        })

# Simpan list dictionary ke dalam file JSON
with open(output_json, "w", encoding="utf-8") as json_file:
    json.dump(hasil_akhir, json_file, indent=4, ensure_ascii=False)
    
print(f"\nSelesai! Semua hasil rangkuman telah disimpan ke '{output_json}'")