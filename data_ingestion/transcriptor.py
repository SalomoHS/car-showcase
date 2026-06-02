from youtube_transcript_api import YouTubeTranscriptApi
import os

# Data video berdasarkan list yang diberikan
videos = [
    # Daih
    {"brand": "mitsubishi", "name": "xforce", "id": "JXLLXD8FfcU"},
]

# Buat folder untuk menyimpan hasil transcript
output_folder = "./src/transcripts"

for video in videos:
    video_id = video["id"]
    filename = f"{output_folder}/{video['brand']}_{video['name']}.txt"
    
    try:
        # Ambil transcript (prioritas bahasa Indonesia 'id', lalu Inggris 'en')
        fetched_transcript = YouTubeTranscriptApi().fetch(video_id, languages=['id', 'en'])
        print(fetched_transcript)
        # Gabungkan semua text
        full_text = "\n".join([snippet.text for snippet in fetched_transcript])
        
        # Simpan ke file txt
        with open(filename, "w", encoding="utf-8") as f:
            f.write(full_text)
            
        print(f"Transcript berhasil disimpan ke {filename}")
        
    except Exception as e:
        print(f"Gagal mengambil transcript untuk {video['brand']} {video['name']} ({video_id}): {e}")