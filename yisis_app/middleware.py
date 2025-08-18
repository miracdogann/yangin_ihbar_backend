from django.core.cache import cache
from .models import SecurityLog
import time

class SecurityLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # İstek öncesi işlemler
        ip = self.get_client_ip(request)
        path = request.path

        # Rate limiting kontrolü
        cache_key = f'request_count_{ip}_{path}'
        request_count = cache.get(cache_key, 0)
        
        # Son 1 dakikadaki istek sayısını kontrol et
        if request_count > 60:  # Dakikada 60 istek limiti
            SecurityLog.objects.create(
                ip_address=ip,
                event_type='DDOS_ATTEMPT',
                severity='CRITICAL',
                request_path=path,
                request_method=request.method,
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                request_count=request_count,
                is_blocked=True,
                details={
                    'headers': dict(request.headers),
                    'params': dict(request.GET),
                }
            )
        else:
            # Normal istek loglama
            if request_count > 30:  # 30'dan fazla istek varsa uyarı oluştur
                SecurityLog.objects.create(
                    ip_address=ip,
                    event_type='RATE_LIMIT',
                    severity='WARNING',
                    request_path=path,
                    request_method=request.method,
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    request_count=request_count
                )

        # İstek sayacını güncelle
        cache.set(cache_key, request_count + 1, 60)  # 60 saniye TTL

        response = self.get_response(request)

        # İstek sonrası işlemler
        if response.status_code in [401, 403]:
            SecurityLog.objects.create(
                ip_address=ip,
                event_type='INVALID_AUTH',
                severity='WARNING',
                request_path=path,
                request_method=request.method,
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                request_count=1
            )

        return response

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')
