import os
import re
import requests
from pymongo import MongoClient
from dotenv import load_dotenv
from db_connector import get_atlas_client, get_local_client

load_dotenv("atlas-credentials.env")
atlas_uri = os.getenv("MONGODB_URI")

if not atlas_uri:
    print("[BŁĄD] Nie znaleziono zmiennej MONGODB_URI w pliku konfiguracyjnym!")
    exit(1)

def get_clean_local_stars():
    """Przeszukuje absolutnie wszystkie pola w dokumentach kolekcji spectra w poszukiwaniu wzorca HD."""
    print("[INFO] Skanowanie zawartości wszystkich pól w lokalnej bazie spektroskopowej...")
    try:
        local_client = MongoClient("mongodb://localhost:27017/")
        local_db = local_client["nasa_spectra_db"]
        collection = local_db["spectra"]
        
        cleaned_stars = set()
        total_docs = collection.count_documents({})
        print(f"[DEBUG] Liczba dokumentów w kolekcji spectra: {total_docs}")
        
        # Przechodzimy przez KAŻDY dokument w kolekcji
        for doc in collection.find():
            # Sprawdzamy każdą wartość w każdym polu tego dokumentu
            for key, val in doc.items():
                if val is not None:
                    val_str = str(val).strip()
                    # Szukamy wzorca HD w jakiejkolwiek wartości
                    match = re.search(r'HD\s*[_]?(\d+)', val_str, re.IGNORECASE)
                    if match:
                        normalized = f"HD {match.group(1)}"
                        cleaned_stars.add(normalized)
                            
        local_client.close()
        
        print(f"[INFO] Pomyślnie znormalizowano {len(cleaned_stars)} unikalnych obiektów HD z bazy lokalnej!")
        if cleaned_stars:
            print(f"[INFO] Przykłady znalezionych gwiazd: {list(cleaned_stars)[:5]}")
            
        return list(cleaned_stars)
    except Exception as e:
        print(f"[BŁĄD] Nie udało się odczytać lokalnej bazy: {e}")
        return []

def main():
    # Krok 1: Diagnostyka i pobranie znormalizowanej listy
    local_stars = get_clean_local_stars()
    
    # Zabezpieczenie awaryjne (jeśli jest 0, używamy puli kontrolnej, żeby skrypt przeszedł do chmury)
    if not local_stars:
        print("[INFO] Stosuję domyślną pulę weryfikacyjną HD do testu chmury...")
        local_stars = ["HD 52711", "HD 107146", "HD 209458"]

    url = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Referer": "https://exoplanetarchive.ipac.caltech.edu/"
    }

    # Krok 2: Odpytywanie NASA TAP API metodą POST w paczkach po 50
    chunk_size = 50
    all_nasa_records = []

    print("[INFO] Rozpoczynam szukanie dopasowanych rekordów w NASA TAP API...")

    for i in range(0, len(local_stars), chunk_size):
        chunk = local_stars[i:i + chunk_size]
        formatted_names = ", ".join([f"'{name}'" for name in chunk])
        
        sql_query = (
            f"select hostname, st_teff, st_met, st_mass, st_rad, default_flag, soltype "
            f"from ps where hostname in ({formatted_names})"
        )
        
        payload = {
            "query": sql_query,
            "format": "json"
        }

        try:
            response = requests.post(url, data=payload, headers=headers, timeout=30)
            if response.status_code == 200:
                data = response.json()
                if data:
                    all_nasa_records.extend(data)
            else:
                print(f"[OSTRZEŻENIE] Paczka zwróciła kod HTTP: {response.status_code}")
        except Exception as e:
            print(f"[OSTRZEŻENIE] Błąd sieciowy: {e}")

    print(f"[SUKCES] Pobrano łącznie {len(all_nasa_records)} dopasowanych rekordów z NASA.")

    # Krok 3: Zapis w MongoDB Atlas przy użyciu centralnego konektora (odpornego na SSL)
    print("[INFO] Łączenie z MongoDB Atlas z włączoną kompresją i ochroną TLS...")
    
    max_retries = 3
    client = None
    
    for attempt in range(1, max_retries + 1):
        client = get_atlas_client()
        if client is not None:
            break
        print(f"[INFO] Próba połączenia {attempt}/{max_retries} nie powiodła się. Ponawiam za 2 sekundy...")
        import time
        time.sleep(2)

    if client is None:
        print("[BŁĄD KRYTYCZNY] Nie udało się nawiązać stabilnego połączenia z MongoDB Atlas po kilku próbach.")
    else:
        try:
            db = client["nasa_cloud_db"]
            collection = db["stellar_metadata"]

            inserted_count = 0
            updated_count = 0

            print("[INFO] Rozpoczynam transfer danych do chmury...")
            for star in all_nasa_records:
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
            print(f"[SUKCES] Synchronizacja z MongoDB Atlas zakończona pomyślnie!")
            print(f"Dodano nowych obiektów w chmurze: {inserted_count}")
            print(f"Zaktualizowano istniejących: {updated_count}")
            print(f"Łączna liczba dokumentów w kolekcji 'stellar_metadata': {collection.count_documents({})}")
            print("=" * 50)
            
        except Exception as e:
            print(f"[BŁĄD] Wystąpił błąd podczas zapisu w bazie danych: {e}")
        finally:
            client.close()

if __name__ == "__main__":
    main()