from django.http import HttpResponse
from rest_framework.views import APIView 
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from django.core.cache import cache
from .models import SecurityLog
import re

class BaseAPIView(APIView):
    def validate_string_field(self, value, field_name, max_length=None, min_length=None, pattern=None):
        if not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a string")
        
        if max_length and len(value) > max_length:
            raise ValidationError(f"{field_name} cannot be longer than {max_length} characters")
            
        if min_length and len(value) < min_length:
            raise ValidationError(f"{field_name} must be at least {min_length} characters")
            
        if pattern and not re.match(pattern, value):
            raise ValidationError(f"{field_name} format is invalid")
            
        return value.strip()

    def validate_email(self, email):
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return self.validate_string_field(email, 'Email', pattern=pattern, max_length=254)

    def validate_phone(self, phone):
        pattern = r'^\+?[0-9]{10,15}$'
        return self.validate_string_field(phone, 'Phone number', pattern=pattern)

    def sanitize_input(self, data):
        if isinstance(data, str):
            return data.replace('<', '&lt;').replace('>', '&gt;')
        elif isinstance(data, dict):
            return {k: self.sanitize_input(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.sanitize_input(item) for item in data]
        return data
from rest_framework import status
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password
from datetime import timedelta
import uuid
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import AuthenticationFailed
from .models import * 
from yisis_app.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication


def home(request):
    return HttpResponse("Yangi İhbar Api")


class Fires(APIView):
    def get(self, request):
        data = {"message": "Yanginlar Api"}
        return Response(data, status=status.HTTP_200_OK)
    

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



class CreateFireReportView(BaseAPIView):
    throttle_classes = [AnonRateThrottle]
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

        if not all([photo_url, latitude, longitude]):
            return Response({"error": "Tüm alanlar gerekli"}, status=status.HTTP_400_BAD_REQUEST)

        report = FireReport.objects.create(
            user=user,
            photo_url=photo_url,
            latitude=latitude,
            longitude=longitude
        )

        return Response({"message": "İhbar başarıyla oluşturuldu", "report_id": report.id}, status=status.HTTP_201_CREATED)


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


class RegisterView(BaseAPIView):
    throttle_classes = [AnonRateThrottle]
    def post(self, request):
        try:
            # Input sanitization
            data = self.sanitize_input(request.data)
            
            # Veri validasyonu
            name_surname = self.validate_string_field(
                data.get("name_surname", ""), 
                "Name and surname", 
                min_length=5, 
                max_length=50
            )
            phone_number = self.validate_phone(data.get("phone_number", ""))
            email = self.validate_email(data.get("email", ""))
            password = self.validate_string_field(
                data.get("password", ""), 
                "Password", 
                min_length=8, 
                pattern=r'^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d@$!%*#?&]{8,}$'
            )
            confirm_password = data.get("confirm_password")

            # Boş alan kontrolü
            if not all([name_surname, phone_number, email, password, confirm_password]):
                return Response({"error": "Tüm alanlar zorunludur."}, status=status.HTTP_400_BAD_REQUEST)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

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
    
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
import logging

# Güvenlik logger'ı
security_logger = logging.getLogger('security')

class BaseRateThrottle(AnonRateThrottle):
    def throttle_failure(self):
        # Rate limit aşıldığında log oluştur
        request = self.request
        SecurityLog.objects.create(
            ip_address=self.get_client_ip(),
            event_type='RATE_LIMIT',
            severity='WARNING',
            request_path=request.path,
            request_method=request.method,
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            request_count=self.get_request_count(),
            details={'rate': self.rate}
        )
        return True

    def get_client_ip(self):
        request = self.request
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')

    def get_request_count(self):
        return cache.get(self.key, 0)

class LoginRateThrottle(BaseRateThrottle):
    rate = '5/minute'
    scope = 'login'

class RegisterRateThrottle(BaseRateThrottle):
    rate = '3/minute'
    scope = 'register'

class FireReportRateThrottle(BaseRateThrottle):
    rate = '10/minute'
    scope = 'fire_report'

class LoginView(BaseAPIView):
    throttle_classes = [LoginRateThrottle]
    def post(self, request):
        try:
            # Input sanitization
            data = self.sanitize_input(request.data)
            
            # Veri validasyonu
            phone_number = self.validate_phone(data.get("phone_number", ""))
            password = self.validate_string_field(
                data.get("password", ""), 
                "Password", 
                min_length=8
            )

            if not phone_number or not password:
                return Response({"error": "Telefon numarası ve şifre zorunludur."}, status=status.HTTP_400_BAD_REQUEST)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(phone_number=phone_number)
        except User.DoesNotExist:
            return Response({"error": "Kullanıcı bulunamadı."}, status=status.HTTP_404_NOT_FOUND)

        if not user.check_password(password):
            # Başarısız giriş denemesini logla
            security_logger.warning(
                'Failed login attempt',
                extra={
                    'request_ip': request.META.get('REMOTE_ADDR'),
                    'phone_number': phone_number,
                }
            )
            return Response({"error": "Şifre hatalı."}, status=status.HTTP_401_UNAUTHORIZED)

        # JWT token oluşturma
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        return Response(
            {
                "message": "Giriş başarılı.",
                "tokens": {
                    "access": access_token,
                    "refresh": refresh_token
                },
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




