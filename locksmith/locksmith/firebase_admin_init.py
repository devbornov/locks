import firebase_admin
from firebase_admin import credentials

# Path to your Firebase service account JSON
cred_path = 'C:/Users/Bornov Engineering/Desktop/back/locks/locksmith/secrets/lockquick-a63b9-firebase-adminsdk-fbsvc-678defaa16.json'

# Initialize Firebase Admin with your service account credentials
cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred)

print("Firebase Admin SDK initialized")
