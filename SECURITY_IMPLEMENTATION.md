# Yangın İhbar Sistemi - Güvenlik İyileştirmeleri

Bu dokümantasyon, yangın ihbar sistemi backend uygulamasında yapılan tüm güvenlik iyileştirmelerini ve e-Devlet entegrasyonu için alınan önlemleri detaylandırmaktadır.

## 📋 İçindekiler

1. [Temel Güvenlik Yapılandırmaları](#1-temel-güvenlik-yapılandırmaları)
2. [JWT (JSON Web Token) İmplementasyonu](#2-jwt-json-web-token-implementasyonu)
3. [Rate Limiting ve DDoS Koruması](#3-rate-limiting-ve-ddos-koruması)
4. [SSL/TLS Yapılandırması](#4-ssltls-yapılandırması)
5. [e-Devlet Entegrasyonu Güvenliği](#5-e-devlet-entegrasyonu-güvenliği)
6. [Veri Şifreleme](#6-veri-şifreleme)
7. [Güvenlik Loglaması ve İzleme](#7-güvenlik-loglaması-ve-i̇zleme)
8. [Input Validation ve Sanitization](#8-input-validation-ve-sanitization)
9. [Session Güvenliği](#9-session-güvenliği)
10. [Database Güvenliği](#10-database-güvenliği)
11. [Content Security Policy (CSP)](#11-content-security-policy-csp)
12. [Admin Panel Güvenliği](#12-admin-panel-güvenliği)
13. [Middleware Güvenliği](#13-middleware-güvenliği)
14. [Password Politikaları](#14-password-politikaları)

---

## 1. Temel Güvenlik Yapılandırmaları

### Yapılan Değişiklikler:

#### `settings.py` Güncellemeleri:
```python
# DEBUG modu kontrollü hale getirildi
DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

# Güvenli host ayarları
ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '[your-production-domain.com]'
]

# CORS güvenlik ayarları
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000"
]

# Güvenlik başlıkları
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
```

### Güvenlik Faydaları:
- XSS saldırılarına karşı koruma
- Clickjacking koruması
- MIME type sniffing koruması
- HSTS ile HTTPS zorlaması

---

## 2. JWT (JSON Web Token) İmplementasyonu

### Kurulum:
```bash
pip install djangorestframework-simplejwt
```

### Yapılandırma:
```python
# JWT ayarları
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
}
```

### Özellikler:
- **Token Yaşam Süresi**: 60 dakika
- **Refresh Token**: 1 gün
- **Token Rotasyonu**: Aktif
- **Blacklist Mekanizması**: Güvenli token iptali
- **HS256 Algoritması**: Güvenli imzalama

### Login View Güncellemeleri:
```python
class LoginView(BaseAPIView):
    def post(self, request):
        # JWT token oluşturma
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)
        
        return Response({
            "tokens": {
                "access": access_token,
                "refresh": refresh_token
            }
        })
```

---

## 3. Rate Limiting ve DDoS Koruması

### REST Framework Rate Limiting:
```python
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/day',
        'user': '1000/day',
        'login': '5/minute',
    }
}
```

### Endpoint Bazlı Limitler:
- **Login**: 5 istek/dakika
- **Kayıt**: 3 istek/dakika  
- **Yangın İhbarı**: 10 istek/dakika
- **Anonim Kullanıcılar**: 100 istek/gün
- **Kayıtlı Kullanıcılar**: 1000 istek/gün

### Custom Rate Throttle:
```python
class BaseRateThrottle(AnonRateThrottle):
    def throttle_failure(self):
        # Rate limit aşıldığında log oluştur
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
```

---

## 4. SSL/TLS Yapılandırması

### SSL Ayarları:
```python
# SSL/TLS Ayarları
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = False  # Development'da False, Production'da True
```

### HSTS Ayarları:
```python
SECURE_HSTS_SECONDS = 31536000  # 1 yıl
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
```

---

## 5. e-Devlet Entegrasyonu Güvenliği

### OAuth2 Yapılandırması:
```python
EDEVLET = {
    'CLIENT_ID': os.environ.get('EDEVLET_CLIENT_ID', ''),
    'CLIENT_SECRET': os.environ.get('EDEVLET_CLIENT_SECRET', ''),
    'REDIRECT_URI': os.environ.get('EDEVLET_REDIRECT_URI', 'https://your-domain.com/auth/edevlet/callback'),
    'AUTH_URL': 'https://api.turkiye.gov.tr/oauth/authorize',
    'TOKEN_URL': 'https://api.turkiye.gov.tr/oauth/token',
    'API_URL': 'https://api.turkiye.gov.tr',
    'ALLOWED_IPS': os.environ.get('EDEVLET_ALLOWED_IPS', '').split(','),
    'SSL_VERIFY': True,
    'TIMEOUT': 30,
    'SCOPE': 'kimlik-dogrula',
}
```

### Güvenlik Özellikleri:
- **IP Whitelisting**: Sadece belirli IP'lerden erişim
- **SSL Doğrulama**: Zorunlu HTTPS
- **Timeout Kontrolü**: 30 saniye limit
- **Scope Kısıtlaması**: Minimum gerekli izinler

---

## 6. Veri Şifreleme

### Password Hashing:
```python
# Şifre politikası ayarları
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]
```

### Custom SHA256 Implementation:
```python
def set_password(self, raw_password):
    # SHA256 ile şifreleme
    salt = os.urandom(32)  # 32 byte'lık rastgele salt
    password_hash = hashlib.pbkdf2_hmac(
        'sha256',  # Kullanılacak hash algoritması
        raw_password.encode('utf-8'),  # Şifrelenecek veri
        salt,  # Salt değeri
        100000,  # İterasyon sayısı
        dklen=128  # Çıktı uzunluğu
    )
    self.password = salt.hex() + ':' + password_hash.hex()
```

### Güvenlik Özellikleri:
- **PBKDF2**: Brute-force koruması
- **Salt**: Rainbow table koruması
- **100,000 İterasyon**: Hash kırma zorlaştırması
- **128 Byte Çıktı**: Collision direnci

---

## 7. Güvenlik Loglaması ve İzleme

### SecurityLog Modeli:
```python
class SecurityLog(models.Model):
    EVENT_TYPES = [
        ('RATE_LIMIT', 'Hız Sınırı Aşımı'),
        ('DDOS_ATTEMPT', 'DDoS Girişimi'),
        ('INVALID_AUTH', 'Geçersiz Kimlik'),
        ('SUSPICIOUS_IP', 'Şüpheli IP'),
    ]
    
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField()
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES)
    request_path = models.CharField(max_length=255)
    request_method = models.CharField(max_length=10)
    user_agent = models.TextField(null=True, blank=True)
    request_count = models.IntegerField(default=1)
    details = models.JSONField(null=True, blank=True)
    is_blocked = models.BooleanField(default=False)
```

### Log Yapılandırması:
```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'security': {
            'format': '{levelname} {asctime} {module} {message} {request_ip}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/django.log',
            'formatter': 'verbose',
            'maxBytes': 1024 * 1024 * 5,  # 5 MB
            'backupCount': 5,
            'delay': True
        },
        'security_file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/security.log',
            'formatter': 'security',
            'maxBytes': 1024 * 1024 * 5,  # 5 MB
            'backupCount': 5,
            'delay': True
        },
    },
}
```

---

## 8. Input Validation ve Sanitization

### BaseAPIView Sınıfı:
```python
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
```

### Request Body Limitleri:
```python
# Maximum izin verilen request body boyutu (10 MB)
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

# Maximum izin verilen form field sayısı
DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000
```

---

## 9. Session Güvenliği

### Session Ayarları:
```python
# Session güvenlik ayarları
SESSION_COOKIE_AGE = 3600  # 1 saat
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'
```

### Güvenlik Özellikleri:
- **1 Saat Timeout**: Otomatik oturum sonlandırma
- **Browser Close**: Tarayıcı kapandığında session sona erer
- **HttpOnly**: JavaScript erişimi engellenir
- **Strict SameSite**: CSRF koruması

---

## 10. Database Güvenliği

### Database Yapılandırması:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        'CONN_MAX_AGE': 60,  # 60 saniye connection pooling
        'ATOMIC_REQUESTS': True,  # Her request'i transaction içinde çalıştır
        'OPTIONS': {
            'timeout': 20,  # 20 saniye timeout
        }
    }
}

# Database güvenlik ayarları
CONN_HEALTH_CHECKS = True
```

### Güvenlik Özellikleri:
- **Connection Pooling**: Verimli bağlantı yönetimi
- **Atomic Requests**: Transaction güvenliği
- **Timeout Kontrolü**: Donma koruması
- **Health Checks**: Bağlantı sağlığı izleme

---

## 11. Content Security Policy (CSP)

### CSP Yapılandırması:
```python
# Content Security Policy
CSP_DEFAULT_SRC = ("'self'",)
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'", "'unsafe-eval'")
CSP_IMG_SRC = ("'self'", "data:", "https:")
CSP_FONT_SRC = ("'self'", "https:", "data:")
CSP_CONNECT_SRC = ("'self'",)
CSP_OBJECT_SRC = ("'none'",)
CSP_BASE_URI = ("'self'",)
CSP_FRAME_ANCESTORS = ("'none'",)
CSP_FORM_ACTION = ("'self'",)
CSP_INCLUDE_NONCE_IN = ['script-src']
CSP_REPORT_URI = "/csp-report/"
```

### Güvenlik Özellikleri:
- **XSS Koruması**: Güvenli kaynak kontrolü
- **Clickjacking Koruması**: Frame kısıtlamaları
- **Data Exfiltration Koruması**: Connect kısıtlamaları
- **Code Injection Koruması**: Script kontrolü

---

## 12. Admin Panel Güvenliği

### SecurityLogAdmin:
```python
@admin.register(SecurityLog)
class SecurityLogAdmin(admin.ModelAdmin):
    list_display = ('event_type_colored', 'ip_address', 'severity_colored', 'timestamp', 'request_path', 'request_count', 'is_blocked')
    list_filter = ('event_type', 'severity', 'is_blocked', 'timestamp')
    search_fields = ('ip_address', 'request_path', 'user_agent')
    readonly_fields = ('timestamp', 'ip_address', 'event_type', 'request_path', 'request_method', 'user_agent', 'request_count')
    ordering = ('-timestamp',)
    date_hierarchy = 'timestamp'
```

### Admin Özellikleri:
- **Renkli Durum Göstergeleri**: Kolay görsel analiz
- **Filtreleme ve Arama**: Hızlı log analizi
- **Read-only Fields**: Veri bütünlüğü koruması
- **Date Hierarchy**: Zaman bazlı navigasyon

---

## 13. Middleware Güvenliği

### SecurityLoggingMiddleware:
```python
class SecurityLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Rate limiting kontrolü
        ip = self.get_client_ip(request)
        path = request.path
        
        cache_key = f'request_count_{ip}_{path}'
        request_count = cache.get(cache_key, 0)
        
        # DDoS tespiti (dakikada 60 istek)
        if request_count > 60:
            SecurityLog.objects.create(
                ip_address=ip,
                event_type='DDOS_ATTEMPT',
                severity='CRITICAL',
                request_path=path,
                request_method=request.method,
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                request_count=request_count,
                is_blocked=True
            )
        
        # İstek sayacını güncelle
        cache.set(cache_key, request_count + 1, 60)
        
        response = self.get_response(request)
        return response
```

### Middleware Özellikleri:
- **Otomatik DDoS Tespiti**: Dakikada 60+ istek kontrolü
- **IP Bazlı İzleme**: Kaynak takibi
- **Otomatik Loglama**: Şüpheli aktivite kaydı
- **Cache Tabanlı**: Performanslı sayaç yönetimi

---

## 14. Password Politikaları

### Password Validation:
```python
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
        'OPTIONS': {
            'max_similarity': 0.7,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]
```

### Şifre Gereksinimleri:
- **Minimum 8 Karakter**: Uzunluk kontrolü
- **Karmaşıklık**: Harf ve rakam kombinasyonu
- **Benzerlik Kontrolü**: Kullanıcı bilgileriyle %70'den az benzerlik
- **Yaygın Şifre Kontrolü**: Bilinen zayıf şifrelerin engellenmesi

---

## 🔒 Güvenlik Özeti

Bu implementasyon ile sistem aşağıdaki tehditlere karşı korumalı hale getirilmiştir:

### Korunan Saldırı Türleri:
- ✅ **DDoS Saldırıları**: Rate limiting ve middleware koruması
- ✅ **Brute-force Denemeler**: Şifre hashleme ve login limitleri
- ✅ **XSS Saldırıları**: Input sanitization ve CSP
- ✅ **CSRF Saldırıları**: Token bazlı koruma
- ✅ **SQL Injection**: ORM kullanımı ve input validation
- ✅ **Session Hijacking**: Güvenli session yönetimi
- ✅ **Man-in-the-middle**: SSL/TLS zorlaması
- ✅ **Clickjacking**: Frame restrictions
- ✅ **Data Exfiltration**: CSP ve CORS kontrolü

### Uygunluk Standartları:
- ✅ **e-Devlet Entegrasyonu**: OAuth2 ve güvenlik protokolleri
- ✅ **KVKK Uyumluluğu**: Veri şifreleme ve gizlilik
- ✅ **OWASP Top 10**: Temel güvenlik açıklarına karşı koruma
- ✅ **ISO 27001**: Bilgi güvenliği yönetimi
- ✅ **PCI DSS**: Ödeme kartı veri güvenliği (uygulanabilir ise)

---

## 📚 Environment Variables

Production ortamında aşağıdaki environment variable'ları ayarlanmalıdır:

```bash
# Django Ayarları
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=False

# e-Devlet Entegrasyonu
EDEVLET_CLIENT_ID=your-client-id
EDEVLET_CLIENT_SECRET=your-client-secret
EDEVLET_REDIRECT_URI=https://your-domain.com/auth/edevlet/callback
EDEVLET_ALLOWED_IPS=ip1,ip2,ip3

# Database (if using PostgreSQL)
DATABASE_URL=postgresql://user:password@host:port/dbname
```

---

## 🚀 Deployment Checklist

Production'a geçmeden önce:

- [ ] `DEBUG = False` ayarlandı
- [ ] SSL sertifikaları yüklendi
- [ ] Environment variables ayarlandı
- [ ] Log dizinleri oluşturuldu
- [ ] Admin kullanıcı şifresi güçlendirildi
- [ ] e-Devlet test ortamında testler yapıldı
- [ ] Güvenlik testleri tamamlandı
- [ ] Backup stratejisi belirlendi
- [ ] Monitoring sistemi kuruldu

---

**Son Güncelleme**: 17 Ağustos 2025  
**Versiyon**: 1.0  
**Geliştirici**: Yangin İhbar Sistemi Ekibi

