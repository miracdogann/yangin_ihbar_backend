import traceback
from google import genai
from google.genai import types

# Gemini client
client = genai.Client(api_key="AIzaSyDy1WEWDCXyVV2ee1N67SORE7QjDsbL6lc")

# İzin verilen görsel formatları
ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
}
MAX_IMAGE_SIZE_MB = 16

def fire_check(image_path, mime_type="image/jpeg"):
    try:
        if mime_type not in ALLOWED_MIME_TYPES:
            return {"error": "Desteklenmeyen dosya formatı."}

        # Görseli oku
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        if len(image_bytes) > MAX_IMAGE_SIZE_MB * 1024 * 1024:
            return {"error": "Görsel boyutu 16MB'den büyük olamaz."}

        # Gemini prompt
        prompt = """
        Sana bir görsel verilecek. Lütfen sadece şunu yap:
        - Eğer görselde açıkça bir YANGIN, ALEV veya YOĞUN DUMAN görülüyorsa yanıt olarak sadece 'EVET' de.
        - Eğer yangınla ilgili hiçbir belirti yoksa 'HAYIR' de.
        - Başka hiçbir şey yazma.
        """

        contents = [
            prompt,
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
        ]

        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=['TEXT']
            )
        )

        result_text = "HAYIR"
        if response.candidates:
            part = response.candidates[0].content.parts[0]
            if hasattr(part, "text") and part.text:
                result_text = part.text.strip().upper()

        if result_text == "EVET":
            return {"ok": True, "message": "Yangın tespit edildi."}
        else:
            return {"ok": False, "message": "Yangın tespit edilmedi."}

    except Exception as e:
        traceback.print_exc()
        return {"error": "Sunucu hatası", "detail": str(e)}

# ---------------------
# Test için kullanım
# ---------------------
if __name__ == "__main__":
    # Buraya test etmek istediğin görsel yolunu yaz
    image_path = "4.jpeg"
    result = fire_check(image_path, mime_type="image/jpeg")
    print(result)
