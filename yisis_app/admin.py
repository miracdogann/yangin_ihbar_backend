from django.contrib import admin
from django.utils.html import format_html
from .models import *

@admin.register(SecurityLog)
class SecurityLogAdmin(admin.ModelAdmin):
    list_display = ('event_type_colored', 'ip_address', 'severity_colored', 'timestamp', 'request_path', 'request_count', 'is_blocked')
    list_filter = ('event_type', 'severity', 'is_blocked', 'timestamp')
    search_fields = ('ip_address', 'request_path', 'user_agent')
    readonly_fields = ('timestamp', 'ip_address', 'event_type', 'request_path', 'request_method', 'user_agent', 'request_count')
    ordering = ('-timestamp',)
    date_hierarchy = 'timestamp'
    
    def event_type_colored(self, obj):
        colors = {
            'RATE_LIMIT': 'orange',
            'DDOS_ATTEMPT': 'red',
            'INVALID_AUTH': 'purple',
            'SUSPICIOUS_IP': 'blue'
        }
        return format_html(
            '<span style="color: {};">{}</span>',
            colors.get(obj.event_type, 'black'),
            obj.get_event_type_display()
        )
    event_type_colored.short_description = 'Olay Tipi'

    def severity_colored(self, obj):
        colors = {
            'INFO': 'green',
            'WARNING': 'orange',
            'CRITICAL': 'red'
        }
        return format_html(
            '<span style="color: {};">{}</span>',
            colors.get(obj.severity, 'black'),
            obj.get_severity_display()
        )
    severity_colored.short_description = 'Önem Derecesi'

    fieldsets = (
        ('Olay Bilgileri', {
            'fields': ('event_type', 'severity', 'timestamp')
        }),
        ('İstek Detayları', {
            'fields': ('ip_address', 'request_path', 'request_method', 'request_count')
        }),
        ('Ek Bilgiler', {
            'fields': ('user_agent', 'details', 'is_blocked'),
            'classes': ('collapse',)
        }),
    )

# Diğer modeller
admin.site.register(User)
admin.site.register(FireStation)
admin.site.register(NasaFireData)
admin.site.register(InfoContent)
admin.site.register(Notification)
admin.site.register(FakeReport)
admin.site.register(FireReport)