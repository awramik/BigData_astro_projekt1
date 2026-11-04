import os
import certifi
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("atlas-credentials.env")

def get_atlas_client():
    """
    Zwraca klienta MongoDB Atlas z certyfikatami certifi i bezpiecznym timeoutem.
    Jeśli połączenie nie powiedzie się, zwraca None.
    """
    atlas_uri = os.getenv("MONGODB_URI")
    if not atlas_uri:
        print("[BŁĄD] Brak zmiennej MONGODB_URI w pliku konfiguracyjnym.")
        return None

    try:
        # Inicjalizacja z certyfikatami certifi i bezpiecznym timeoutem
        client = MongoClient(
            atlas_uri,
            tlsCAFile=certifi.where(),
            serverSelectionTimeoutMS=15000,
            connectTimeoutMS=15000
        )
        
        # Test połączenia
        client.admin.command('ping')
        return client
        
    except Exception as e:
        print(f"[OSTRZEŻENIE SIECIOWE] Problem z połączeniem z Atlasem: {e}")
        return None

def get_local_client():
    """Zwraca klienta lokalnej bazy MongoDB."""
    try:
        return MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=2000)
    except Exception as e:
        print(f"[BŁĄD] Nie można połączyć się z lokalną bazą MongoDB: {e}")
        return None