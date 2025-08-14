from django.contrib import admin
from .models import * 
# Register your models here.

admin.site.register(User)
admin.site.register(FireStation)
admin.site.register(NasaFireData)
admin.site.register(InfoContent)
admin.site.register(Notification)
admin.site.register(FakeReport)
admin.site.register(FireReport)