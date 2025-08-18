from django.db import models
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password
import hashlib
import os

class User(models.Model):
    user_name_surname = models.CharField("Ad-Soyad", max_length=50)
    email = models.EmailField("E-posta", unique=True)
    phone_number = models.CharField("Telefon", max_length=15, unique=True)
    password = models.CharField("Parola", max_length=128)  # hash'li şekilde saklanacak

    # Durum alanları
    is_active = models.BooleanField(default=True)
    is_suspended = models.BooleanField(default=False)
    fake_report_count = models.PositiveIntegerField(default=0)
    date_joined = models.DateTimeField(default=timezone.now)
    kvkk_onay = models.BooleanField(default=True)

    # Şifre sıfırlama alanı
    reset_token = models.CharField(max_length=255, blank=True, null=True)
    reset_token_expire = models.DateTimeField(blank=True, null=True)
    # Yeni: Kullanıcı token alanı
    auth_token = models.CharField(max_length=255, blank=True, null=True, unique=True)

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
        # Salt ve hash'i birleştirip base64 ile encode ediyoruz
        self.password = salt.hex() + ':' + password_hash.hex()

    def check_password(self, raw_password):
        try:
            salt_hex, hash_hex = self.password.split(':')
            salt = bytes.fromhex(salt_hex)
            stored_hash = bytes.fromhex(hash_hex)
            
            # Girilen şifreyi aynı yöntemle hash'liyoruz
            password_hash = hashlib.pbkdf2_hmac(
                'sha256',
                raw_password.encode('utf-8'),
                salt,
                100000,
                dklen=128
            )
            return password_hash == stored_hash
        except Exception:
            return False  # Hata durumunda False döndür

    def __str__(self):
        return f"{self.user_name_surname} - {self.email}"

# Yangın İhbarı
class FireReport(models.Model):
    STATUS_CHOICES = [
        ('devam', 'Devam Ediyor'),
        ('mudahale', 'Müdahale Ediliyor'),
        ('sonduruldu', 'Söndürüldü'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="fire_reports")
    photo_url = models.URLField("Yangın Fotoğraf URL", max_length=500 ,blank=True)  # Harici sunucu linki
    latitude = models.FloatField()
    longitude = models.FloatField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='devam')
    timestamp = models.DateTimeField(default=timezone.now)
    is_confirmed = models.BooleanField(default=False)

    def __str__(self):
        return f"Yangın İhbarı - {self.user.user_name_surname} ({self.timestamp.strftime('%Y-%m-%d %H:%M')})"


# İtfaiye İstasyonları
class FireStation(models.Model):
    name = models.CharField(max_length=100)
    latitude = models.FloatField()
    longitude = models.FloatField()
    address = models.TextField(blank=True)
    phone_number = models.CharField("Telefon", max_length=15,blank=True)

    def __str__(self):
        return self.name


# NASA Yangın Verisi (günlük güncellenebilir)
class NasaFireData(models.Model):
    latitude = models.FloatField()
    longitude = models.FloatField()
    brightness = models.FloatField()
    confidence = models.CharField(max_length=10)
    timestamp = models.DateTimeField()

    def __str__(self):
        return f"NASA Yangın ({self.timestamp.strftime('%Y-%m-%d %H:%M')})"


# Bilgilendirici İçerikler (yangın öncesi / anı / sonrası)
class InfoContent(models.Model):
    CATEGORY_CHOICES = [
        ('oncesi', 'Yangın Öncesi'),
        ('ani', 'Yangın Anı'),
        ('sonrasi', 'Yangın Sonrası'),
    ]
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    content = models.TextField()

    def __str__(self):
        return self.title


# Bildirim Geçmişi
class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    related_report = models.ForeignKey(FireReport, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Bildirim -> {self.user.user_name_surname}"


# Asılsız İhbar Raporları (yönetici işlem başlatabilir)
class FakeReport(models.Model):
    report = models.ForeignKey(FireReport, on_delete=models.CASCADE)
    reason = models.TextField()
    reviewed_by_admin = models.BooleanField(default=False)
    reported_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Asılsız İhbar - {self.report.user.user_name_surname}"

# DDoS ve Güvenlik Logları
class SecurityLog(models.Model):
    SEVERITY_CHOICES = [
        ('INFO', 'Bilgi'),
        ('WARNING', 'Uyarı'),
        ('CRITICAL', 'Kritik'),
    ]
    
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

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['ip_address']),
            models.Index(fields=['event_type']),
            models.Index(fields=['timestamp']),
        ]

    def __str__(self):
        return f"{self.event_type} - {self.ip_address} ({self.timestamp.strftime('%Y-%m-%d %H:%M:%S')})"