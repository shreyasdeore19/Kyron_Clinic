from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.index, name='index'),
    path('api/send-message/', views.send_message, name='send_message'),
    path('api/voice-call/', views.initiate_voice_call, name='voice_call'),
    path('api/reset/', views.reset_session, name='reset'),
    path('api/sms-opt-in/', views.opt_in_sms, name='sms_opt_in'),
]
