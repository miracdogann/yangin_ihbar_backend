from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import redirect, render
from django.db.models import Count
from .models import *
import json
from django import forms

# ModelForm özelleştirme
class FireReportForm(forms.ModelForm):
    class Meta:
        model = FireReport
        fields = '__all__'
        widgets = {
            'photo_url': forms.URLInput(attrs={'style': 'width: 100%'}),
        }

@admin.register(FireReport)
class FireReportAdmin(admin.ModelAdmin):
    form = FireReportForm
    list_display = ("id", "ihbar_sahibi_bilgileri", "tarih_saat", "durum_renkli", "foto_önizleme", "photo_url", "islemler")
    list_editable = ("photo_url",)
    list_filter = ("status", "is_confirmed", "timestamp")
    search_fields = ("user__user_name_surname", "user__email", "user__phone_number")
    ordering = ("-timestamp",)
    fieldsets = (
        (None, {
            'fields': ('user', 'photo_url', 'latitude', 'longitude', 'status', 'address', 'is_confirmed',"description")
        }),
    )
    
    # İhbar sahibi bilgileri
    def ihbar_sahibi_bilgileri(self, obj):
        return format_html(
            '{}<br><small style="color: #666;">E-posta: {}<br>Telefon: {}</small>',
            obj.user.user_name_surname,
            obj.user.email,
            obj.user.phone_number or "-"
        )
    ihbar_sahibi_bilgileri.short_description = "İhbar Sahibi"

    # Tarih ve saat formatı
    def tarih_saat(self, obj):
        return obj.timestamp.strftime("%d.%m.%Y %H:%M:%S")
    tarih_saat.short_description = "Tarih / Saat"

    # Durum renkli gösterimi
    def durum_renkli(self, obj):
        renkler = {
            "devam": "#f4a261",
            "mudahale": "#2a9d8f",
            "sonduruldu": "#2b9348"
        }
        durum_ismi = {
            "devam": "Devam Ediyor",
            "mudahale": "Müdahale Ediliyor",
            "sonduruldu": "Söndürüldü"
        }
        return format_html(
            '<span style="background:{}; color:white; padding:4px 8px; border-radius:4px; display:inline-block;">{}</span>',
            renkler.get(obj.status, "#666"),
            durum_ismi.get(obj.status, obj.get_status_display())
        )
    durum_renkli.short_description = "Durum"

    # Fotoğraf önizleme
    def foto_önizleme(self, obj):
        if obj.photo_url:
            return format_html(
                '<img src="{}" style="height:50px; border-radius:4px; border:1px solid #ddd;" />',
                obj.photo_url
            )
        return "-"
    foto_önizleme.short_description = "Fotoğraf"

    # İşlemler (Durum güncelleme butonları)
    def islemler(self, obj):
        return format_html(
            '''
            <div style="display:flex; gap:5px;">
                <a class="button" style="background:#f4a261; color:white; padding:6px 12px; border-radius:4px; text-decoration:none;" 
                   href="set_status/{}/devam">Devam</a>
                <a class="button" style="background:#2a9d8f; color:white; padding:6px 12px; border-radius:4px; text-decoration:none;" 
                   href="set_status/{}/mudahale">Müdahale</a>
                <a class="button" style="background:#2b9348; color:white; padding:6px 12px; border-radius:4px; text-decoration:none;" 
                   href="set_status/{}/sonduruldu">Söndürüldü</a>
            </div>
            ''',
            obj.id, obj.id, obj.id
        )
    islemler.short_description = "Durum Güncelle"

    # Custom URL'ler
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("set_status/<int:report_id>/<str:status>", 
                 self.admin_site.admin_view(self.set_status),
                 name="set_fire_report_status")
        ]
        return custom_urls + urls

    # Durum güncelleme fonksiyonu
    def set_status(self, request, report_id, status):
        try:
            report = FireReport.objects.get(id=report_id)
            report.status = status
            report.save()
            self.message_user(request, f"İhbar durumu başarıyla '{report.get_status_display()}' olarak güncellendi ✅")
        except FireReport.DoesNotExist:
            self.message_user(request, "İhbar bulunamadı!", level="error")
        return redirect("admin:yisis_app_firereport_changelist")

    # Onaylama aksiyonu
    actions = ["mark_as_confirmed"]

    def mark_as_confirmed(self, request, queryset):
        updated = queryset.update(is_confirmed=True)
        self.message_user(request, f"{updated} ihbar onaylandı ✅")
    mark_as_confirmed.short_description = "Seçili ihbarları onayla"

    # Admin paneli özelleştirme
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['extra_css'] = '''
            <style>
                .field-islemler .button:hover { opacity: 0.8; }
                .field-durum_renkli { min-width: 120px; }
                .field-ihbar_sahibi_bilgileri { min-width: 200px; }
                .field-tarih_saat { min-width: 120px; }
                table { font-size: 14px; }
                th, td { padding: 8px 10px; }
            </style>
        '''
        return super().changelist_view(request, extra_context=extra_context)

# Diğer modellerin kayıtları
admin.site.register(User)
admin.site.register(FireStation)
admin.site.register(NasaFireData)
admin.site.register(InfoContent)
admin.site.register(Notification)
admin.site.register(FakeReport)