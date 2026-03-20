from django.contrib import admin
from .models import ChatSession, ChatMessage, Appointment


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'first_name', 'last_name', 'current_state', 'created_at')
    list_filter = ('current_state',)
    search_fields = ('first_name', 'last_name', 'email')


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('session', 'role', 'content', 'timestamp')
    list_filter = ('role',)


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient_first_name', 'patient_last_name', 'doctor_name', 'appointment_date', 'appointment_time', 'confirmed')
    list_filter = ('confirmed', 'doctor_name')
    search_fields = ('patient_first_name', 'patient_last_name', 'patient_email')
