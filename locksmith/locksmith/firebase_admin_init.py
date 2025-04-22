import firebase_admin
from firebase_admin import credentials

cred = credentials.Certificate("secrets/firebase-adminsdk.json")
firebase_admin.initialize_app(cred)
