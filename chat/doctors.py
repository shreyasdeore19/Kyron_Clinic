"""
Hard-coded doctor availability data for the next 30-60 days.
Each doctor specializes in a different body part/system.
"""
from datetime import datetime, timedelta
import random

DOCTORS = [
    {
        "id": "dr_chen",
        "name": "Dr. Sarah Chen",
        "title": "Orthopedic Specialist",
        "specialty": "Musculoskeletal & Joint Care",
        "body_parts": [
            "knee", "hip", "shoulder", "elbow", "wrist", "ankle",
            "back", "spine", "neck", "joint", "bone", "fracture",
            "arthritis", "tendon", "ligament", "muscle", "sports injury",
            "leg", "arm", "hand", "foot",
        ],
        "bio": "Board-certified orthopedic surgeon with 15 years of experience in joint replacement and sports medicine.",
        "office": "Kyron Medical - Suite 200, 450 Brookline Ave, Boston, MA 02215",
    },
    {
        "id": "dr_patel",
        "name": "Dr. Raj Patel",
        "title": "Cardiologist",
        "specialty": "Heart & Cardiovascular Care",
        "body_parts": [
            "heart", "chest", "cardiovascular", "blood pressure",
            "cholesterol", "arrhythmia", "palpitations", "circulation",
            "vein", "artery", "cardiac", "heartbeat", "chest pain",
            "shortness of breath", "hypertension",
        ],
        "bio": "Fellowship-trained cardiologist specializing in preventive cardiology and heart rhythm disorders.",
        "office": "Kyron Medical - Suite 305, 450 Brookline Ave, Boston, MA 02215",
    },
    {
        "id": "dr_martinez",
        "name": "Dr. Elena Martinez",
        "title": "Gastroenterologist",
        "specialty": "Digestive & Gastrointestinal Care",
        "body_parts": [
            "stomach", "abdomen", "digestive", "intestine", "colon",
            "liver", "gallbladder", "pancreas", "acid reflux", "heartburn",
            "nausea", "ibs", "bowel", "gut", "esophagus", "abdominal pain",
            "bloating", "constipation", "diarrhea",
        ],
        "bio": "Gastroenterology specialist with expertise in inflammatory bowel disease and advanced endoscopy.",
        "office": "Kyron Medical - Suite 110, 450 Brookline Ave, Boston, MA 02215",
    },
    {
        "id": "dr_thompson",
        "name": "Dr. Michael Thompson",
        "title": "Neurologist",
        "specialty": "Brain & Nervous System Care",
        "body_parts": [
            "head", "brain", "headache", "migraine", "nerve",
            "numbness", "tingling", "seizure", "memory", "dizziness",
            "vertigo", "tremor", "neurological", "concussion",
            "neuropathy", "sciatica", "multiple sclerosis",
        ],
        "bio": "Neurologist with subspecialty training in headache medicine and neurodegenerative disorders.",
        "office": "Kyron Medical - Suite 420, 450 Brookline Ave, Boston, MA 02215",
    },
    {
        "id": "dr_williams",
        "name": "Dr. Aisha Williams",
        "title": "Dermatologist",
        "specialty": "Skin, Hair & Nail Care",
        "body_parts": [
            "skin", "rash", "acne", "eczema", "mole", "psoriasis",
            "hair", "nail", "dermatitis", "itching", "hives",
            "sunburn", "skin cancer", "wound", "scar", "wart",
            "fungal", "allergy skin",
        ],
        "bio": "Dermatologist specializing in medical and cosmetic dermatology, with expertise in skin cancer screening.",
        "office": "Kyron Medical - Suite 150, 450 Brookline Ave, Boston, MA 02215",
    },
]

PRACTICE_INFO = {
    "name": "Kyron Medical Practice",
    "address": "450 Brookline Ave, Boston, MA 02215",
    "phone": "(617) 555-0100",
    "hours": {
        "Monday": "8:00 AM - 6:00 PM",
        "Tuesday": "8:00 AM - 6:00 PM",
        "Wednesday": "8:00 AM - 6:00 PM",
        "Thursday": "8:00 AM - 7:00 PM",
        "Friday": "8:00 AM - 5:00 PM",
        "Saturday": "9:00 AM - 1:00 PM",
        "Sunday": "Closed",
    },
    "website": "https://www.kyronmedical.com",
}


def generate_availability(doctor_id: str, days_ahead: int = 45) -> list[dict]:
    """Generate realistic appointment slots for a doctor over the next N days."""
    random.seed(hash(doctor_id))
    slots = []
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    time_slots = [
        "9:00 AM", "9:30 AM", "10:00 AM", "10:30 AM", "11:00 AM", "11:30 AM",
        "1:00 PM", "1:30 PM", "2:00 PM", "2:30 PM", "3:00 PM", "3:30 PM",
        "4:00 PM", "4:30 PM",
    ]

    for day_offset in range(1, days_ahead + 1):
        date = today + timedelta(days=day_offset)
        weekday = date.weekday()

        if weekday == 6:  # Sunday
            continue
        if weekday == 5:  # Saturday — fewer slots
            available_times = random.sample(time_slots[:6], k=random.randint(1, 3))
        else:
            available_times = random.sample(time_slots, k=random.randint(3, 8))

        for t in sorted(available_times, key=lambda x: datetime.strptime(x, "%I:%M %p")):
            slots.append({
                "date": date.strftime("%Y-%m-%d"),
                "day_of_week": date.strftime("%A"),
                "time": t,
                "doctor_id": doctor_id,
            })

    return slots


def get_all_availability() -> dict:
    """Return availability keyed by doctor_id."""
    return {doc["id"]: generate_availability(doc["id"]) for doc in DOCTORS}


def find_doctor_for_body_part(body_part: str) -> dict | None:
    """Simple keyword matching — the AI layer does the semantic heavy lifting."""
    body_part_lower = body_part.lower()
    for doc in DOCTORS:
        for keyword in doc["body_parts"]:
            if keyword in body_part_lower or body_part_lower in keyword:
                return doc
    return None


def get_doctor_by_id(doctor_id: str) -> dict | None:
    for doc in DOCTORS:
        if doc["id"] == doctor_id:
            return doc
    return None
