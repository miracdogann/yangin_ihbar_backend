from django.http import HttpResponse
from rest_framework.views import APIView 
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
import uuid
from .models import * 
import requests
from google import genai







def home(request):
    return HttpResponse("Yangi İhbar Api")



class Stations(APIView):
    def get(self,request):
        stations = FireStation.objects.all() # tüm istastonlar
        data = []
        for station in stations:
            data.append({
                "id": station.id,
                "name": station.name,
                "latitude": station.latitude,
                "longitude": station.longitude,
                "address": station.address,
                "phone_number": station.phone_number,
            })
        return Response(data, status=status.HTTP_200_OK)

class Infos(APIView):
    def get(self,request):
        data = {"message": "Bigiler Api"}
        return Response(data, status=status.HTTP_200_OK)

class UserInfoView(APIView):
    def get(self, request):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return Response({"error": "Authorization header missing or invalid"}, status=status.HTTP_401_UNAUTHORIZED)

        token = auth_header[len("Bearer "):]
        try:
            user = User.objects.get(auth_token=token)
        except User.DoesNotExist:
            return Response({"error": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED)

        return Response({
            "id": user.id,
            "name_surname": user.user_name_surname,
            "email": user.email,
            "phone_number": user.phone_number,
        }, status=status.HTTP_200_OK)





# Gemini API konfigürasyonu
GEMINI_API_KEY = "AIzaSyDy1WEWDCXyVV2ee1N67SORE7QjDsbL6lc"
client = genai.Client(api_key=GEMINI_API_KEY)

class CreateFireReportView(APIView):
    def post(self, request):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return Response({"error": "Authorization header missing or invalid"}, status=status.HTTP_401_UNAUTHORIZED)

        token = auth_header[len("Bearer "):]
        try:
            user = User.objects.get(auth_token=token)
        except User.DoesNotExist:
            return Response({"error": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED)

        photo_url = request.data.get("photo_url")
        latitude = request.data.get("latitude")
        longitude = request.data.get("longitude")
        address = request.data.get("address")

        if not all([photo_url, latitude, longitude]):
            return Response({"error": "Tüm alanlar gerekli"}, status=status.HTTP_400_BAD_REQUEST)

        # Fotoğrafı URL'den indir
        try:
            response = requests.get(photo_url)
            response.raise_for_status()
            image_data = response.content
        except requests.RequestException as e:
            return Response({"error": "Fotoğraf indirilemedi", "detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Gemini ile yangın analizi
        try:
            prompt = """
            Bu görselde yangın, duman veya alev var mı? Lütfen dikkatlice inceleyin.
            Yanıtınızı şu formatta verin: 
            "SONUÇ: EVET" - Eğer yangın, duman veya alev tespit ederseniz
            "SONUÇ: HAYIR" - Eğer yangın, duman veya alev tespit etmezseniz
            Ardından kısa bir açıklama ekleyin.
            """

            contents = [
                prompt,
                genai.types.Part.from_bytes(data=image_data, mime_type="image/jpeg"),
            ]

            response = client.models.generate_content(
                model="gemini-2.0-flash-exp-image-generation",
                contents=contents,
            )

            # Gemini yanıtını analiz et
            response_text = response.text if response.text else ""
            
            # SONUÇ: EVET veya SONUÇ: HAYIR formatını kontrol et
            if "SONUÇ: EVET" in response_text:
                # Yangın tespit edildi - ihbar oluştur
                report = FireReport.objects.create(
                    user=user,
                    photo_url=photo_url,
                    latitude=latitude,
                    longitude=longitude,
                    address=address if address else None
                )
                
                return Response({
                    "message": "Yangın ihbarı başarıyla oluşturuldu", 
                    "report_id": report.id,
                    "gemini_response": response_text
                }, status=status.HTTP_201_CREATED)
                
            else:
                # Yangın tespit edilmedi
                return Response({
                    "error": "Yangın tespit edilmedi, ihbar yapılamaz.",
                    "detail": response_text
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                "error": "Yangın analiz hatası", 
                "detail": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class UpdatePushTokenView(APIView):
    def patch(self, request):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return Response({"error": "Authorization header missing or invalid"}, status=status.HTTP_401_UNAUTHORIZED)
        
        token = auth_header[len("Bearer "):]
        try:
            user = User.objects.get(auth_token=token)
        except User.DoesNotExist:
            return Response({"error": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED)
        
        expo_token = request.data.get("expo_push_token")
        if not expo_token:
            return Response({"error": "Expo token gerekli"}, status=status.HTTP_400_BAD_REQUEST)
        
        user.expo_push_token = expo_token
        user.save()
        
        return Response({"message": "Expo token güncellendi"}, status=status.HTTP_200_OK)
# 1) Tüm ihbarlar, token gerektirmez
class ListAllFireReportsView(APIView):
    def get(self, request):
        reports = FireReport.objects.all().order_by("-id")

        def mask_name(full_name):
            # İsim ve soyismi ayır
            parts = full_name.split(" ")
            masked_parts = []

            for part in parts:
                if len(part) <= 2:
                    masked_parts.append(part[0] + "*")
                else:
                    first = part[0:2]  # İlk 2 harf
                    masked = "*" * (len(part) - 2)
                    masked_parts.append(first + masked)
            return " ".join(masked_parts)

        data = [
            {
                "id": report.id,
                "user_id": report.user.id,
                "user_name_masked": mask_name(report.user.user_name_surname),
                "photo_url": report.photo_url,
                "latitude": report.latitude,
                "longitude": report.longitude,
                "address":report.address,
                "status": report.status
            }
            for report in reports
        ]
        return Response(data, status=status.HTTP_200_OK)

# 2) Sadece token ile giriş yapan kullanıcının ihbarları
class ListUserFireReportsView(APIView):
    def get(self, request):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return Response({"error": "Authorization header missing or invalid"}, status=status.HTTP_401_UNAUTHORIZED)

        token = auth_header[len("Bearer "):]
        try:
            user = User.objects.get(auth_token=token)
        except User.DoesNotExist:
            return Response({"error": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED)

        reports = FireReport.objects.filter(user=user).order_by("-id")
        data = [
            {
                "id": report.id,
                "photo_url": report.photo_url,
                "latitude": report.latitude,
                "longitude": report.longitude,
            }
            for report in reports
        ]
        return Response(data, status=status.HTTP_200_OK)


class RegisterView(APIView):
    def post(self, request):
        data = request.data
        name_surname = data.get("name_surname")
        phone_number = data.get("phone_number")
        email = data.get("email")
        password = data.get("password")
        confirm_password = data.get("confirm_password")

        # Boş alan kontrolü
        if not all([name_surname, phone_number, email, password, confirm_password]):
            return Response({"error": "Tüm alanlar zorunludur."}, status=status.HTTP_400_BAD_REQUEST)

        # Şifre eşleşme kontrolü
        if password != confirm_password:
            return Response({"error": "Şifreler eşleşmiyor."}, status=status.HTTP_400_BAD_REQUEST)

        # Email / telefon kontrolü
        if User.objects.filter(email=email).exists():
            return Response({"error": "Bu e-posta zaten kayıtlı."}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(phone_number=phone_number).exists():
            return Response({"error": "Bu telefon numarası zaten kayıtlı."}, status=status.HTTP_400_BAD_REQUEST)
        # Benzersiz token oluştur
        user_token = str(uuid.uuid4())
        # Kullanıcı oluşturma
        user = User(
            user_name_surname=name_surname,
            email=email,
            phone_number=phone_number,
            auth_token=user_token,

        )
        user.set_password(password)
        user.save()

        return Response({
            "message": "Kayıt başarılı.",
            "token": user_token,
            "user": {
                "id": user.id,
                "name_surname": user.user_name_surname,
                "email": user.email,
                "phone_number": user.phone_number,
            }
        }, status=status.HTTP_201_CREATED)
    
class LoginView(APIView):
    def post(self, request):
        data = request.data
        phone_number = data.get("phone_number")
        password = data.get("password")

        if not phone_number or not password:
            return Response({"error": "Telefon numarası ve şifre zorunludur."}, status=status.HTTP_400_BAD_REQUEST)

        # Telefon numarası ile kullanıcı bulma
        try:
            user = User.objects.get(phone_number=phone_number)
        except User.DoesNotExist:
            return Response({"error": "Kullanıcı bulunamadı."}, status=status.HTTP_404_NOT_FOUND)

        # Şifre doğrulama
        if not user.check_password(password):
            return Response({"error": "Şifre hatalı."}, status=status.HTTP_401_UNAUTHORIZED)

        return Response(
            {
                "message": "Giriş başarılı.",
                "token": user.auth_token,
                "user": {
                    "id": user.id,
                    "name_surname": user.user_name_surname,
                    "email": user.email,
                    "phone_number": user.phone_number,
                },
            },
            status=status.HTTP_200_OK,
        )

# şuan şifre değiştirme , sıfırlama ,  unutma kısımları yok daha sonra yapılacak 

class ForgotPasswordView(APIView):
    def post(self, request):
        email = request.data.get("email")

        if not email:
            return Response({"error": "E-posta zorunludur."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "Bu e-posta ile kayıtlı kullanıcı bulunamadı."}, status=status.HTTP_404_NOT_FOUND)

        # Token üretme (örnek: UUID)
        reset_token = str(uuid.uuid4())
        user.reset_token = reset_token
        user.reset_token_expire = timezone.now() + timedelta(minutes=30)  # 30 dk geçerli
        user.save()

        # Burada e-posta veya SMS ile token gönderilebilir
        return Response({"message": "Şifre sıfırlama bağlantısı gönderildi.", "reset_token": reset_token})


class ResetPasswordView(APIView):
    def post(self, request):
        token = request.data.get("token")
        new_password = request.data.get("new_password")
        confirm_password = request.data.get("confirm_password")

        if not all([token, new_password, confirm_password]):
            return Response({"error": "Tüm alanlar zorunludur."}, status=status.HTTP_400_BAD_REQUEST)

        if new_password != confirm_password:
            return Response({"error": "Şifreler eşleşmiyor."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(reset_token=token)
        except User.DoesNotExist:
            return Response({"error": "Geçersiz token."}, status=status.HTTP_400_BAD_REQUEST)

        if timezone.now() > user.reset_token_expire:
            return Response({"error": "Token süresi dolmuş."}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.reset_token = None
        user.reset_token_expire = None
        user.save()

        return Response({"message": "Şifre başarıyla güncellendi."}, status=status.HTTP_200_OK)