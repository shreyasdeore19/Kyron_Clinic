from django.db import models
import uuid


class ChatSession(models.Model):
    session_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Patient info (populated during intake)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    sms_opt_in = models.BooleanField(default=False)

    # Workflow state
    STATE_CHOICES = [
        ('greeting', 'Greeting'),
        ('intake', 'Patient Intake'),
        ('reason', 'Reason for Visit'),
        ('matching', 'Doctor Matching'),
        ('scheduling', 'Scheduling'),
        ('confirmation', 'Confirmation'),
        ('general', 'General Inquiry'),
        ('completed', 'Completed'),
    ]
    current_state = models.CharField(max_length=20, choices=STATE_CHOICES, default='greeting')

    # Appointment details
    matched_doctor_id = models.CharField(max_length=50, blank=True)
    appointment_date = models.CharField(max_length=20, blank=True)
    appointment_time = models.CharField(max_length=20, blank=True)
    reason_for_visit = models.TextField(blank=True)

    # Voice handoff
    voice_call_initiated = models.BooleanField(default=False)
    vapi_call_id = models.CharField(max_length=100, blank=True)

    def __str__(self):
        name = f"{self.first_name} {self.last_name}".strip() or "Anonymous"
        return f"Session {self.session_id} - {name}"


class ChatMessage(models.Model):
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=[('user', 'User'), ('assistant', 'Assistant'), ('system', 'System')])
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"[{self.role}] {self.content[:80]}"


class Appointment(models.Model):
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='appointments')
    patient_first_name = models.CharField(max_length=100)
    patient_last_name = models.CharField(max_length=100)
    patient_email = models.EmailField()
    patient_phone = models.CharField(max_length=20)
    patient_dob = models.DateField()
    doctor_id = models.CharField(max_length=50)
    doctor_name = models.CharField(max_length=200)
    appointment_date = models.CharField(max_length=20)
    appointment_time = models.CharField(max_length=20)
    reason = models.TextField()
    confirmed = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    confirmation_email_sent = models.BooleanField(default=False)
    confirmation_sms_sent = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.patient_first_name} {self.patient_last_name} - {self.doctor_name} on {self.appointment_date}"
