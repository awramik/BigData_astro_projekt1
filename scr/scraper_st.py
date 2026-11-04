import os
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("atlas-credentials.env")
atlas_uri = os.getenv("MONGODB_URI")

if not atlas_uri:
    print("[BŁĄD] Nie znaleziono zmiennej MONGODB_URI w pliku konfiguracyjnym!")
    exit(1)

def main():
    print("[INFO] Łączenie z bazą w chmurze (MongoDB Atlas)...")
    try:
        client = MongoClient(atlas_uri)
        db = client["nasa_cloud_db"]
        collection = db["stellar_metadata"]
        
        # Test połączenia z chmurą
        client.admin.command('ping')
        print("[SUKCES] Połączenie z MongoDB Atlas nawiązane pomyślnie!")
    except Exception as e:
        print(f"[BŁĄD] Nie udało się połączyć z chmurą: {e}")
        return

    # Oficjalny endpoint NASA Exoplanet Archive TAP API
    # Pobieramy pełne rekordy zawierające identyfikator, parametry fizyczne, 
    # a także flagi statusów (default_flag, soltype) oraz źródła bibliograficzne (refname).
    query_url = (
        "https://exoplanetarchive.ipac.caltech.edu/TAP/sync?"
        "query=select+top+500+hostname,st_teff,st_met,st_mass,st_rad,default_flag,soltype,pl_refname,st_refname+"
        "from+ps+where+st_teff+is+not+null&format=json"
    )
    
    print("[INFO] Pobieranie surowych danych wraz ze źródłami i statusami z NASA Exoplanet Archive...")

    try:
        response = requests.get(query_url, timeout=15)
        if response.status_code != 200:
            print(f"[BŁĄD] Serwer NASA zwrócił kod: {response.status_code}")
            return

        stars_data = response.json()
        print(f"[SUKCES] Pobrano {len(stars_data)} surowych rekordów z NASA.")

        # Idempotentny zapis w chmurze MongoDB Atlas
        inserted_count = 0
        updated_count = 0

        for star in stars_data:
            hostname = star.get("hostname")
            if not hostname:
                continue

            result = collection.update_one(
                {"hostname": hostname},
                {"$set": star},
                upsert=True
            )
            
            if result.upserted_id:
                inserted_count += 1
            elif result.modified_count > 0:
                updated_count += 1

        print("=" * 50)
        print(f"[SUKCES] Synchronizacja z MongoDB Atlas zakończona!")
        print(f"Dodano nowych obiektów: {inserted_count}")
        print(f"Zaktualizowano istniejących: {updated_count}")
        print(f"Łączna liczba dokumentów w kolekcji 'stellar_metadata': {collection.count_documents({})}")
        print("=" * 50)

    except Exception as e:
        print(f"[BŁĄD] Wystąpił błąd podczas pobierania lub zapisu danych: {e}")

if __name__ == "__main__":
    main()