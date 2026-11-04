import os
from pymongo import MongoClient

# Połączenie z lokalną bazą MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["nasa_spectra_db"]
collection = db["spectra"]

def audit_and_clean_data():
    """
    Moduł czyszczenia i walidacji danych (Data Cleaning & Audit):
    1. Sprawdza spójność strukturalną dokumentów (czy mają metadane i pomiary).
    2. Wykrywa i usuwa dokumenty wadliwe lub puste.
    3. Normalizuje brakujące pola tekstowe (np. nazwy gwiazd).
    """
    print("=" * 60)
    print("--- [03_cleaner.py] SPRAWDZENIE I CZYSZCZENIE DANYCH W MONGODB ---")
    print("=" * 60)
    
    total_before = collection.count_documents({})
    print(f"[STAN PRZED] Łączna liczba dokumentów w kolekcji: {total_before}")
    
    # 1. Sprawdzanie braków kluczowych pól (Data Verification / Audyt)
    missing_metadata = collection.count_documents({"metadata": {"$exists": False}})
    missing_measurements = collection.count_documents({"measurements": {"$exists": False}})
    empty_measurements = collection.count_documents({"measurements_count": {"$lte": 0}})
    
    print(f"[SPRAWDZENIE] Dokumenty bez pola 'metadata': {missing_metadata}")
    print(f"[SPRAWDZENIE] Dokumenty bez pola 'measurements': {missing_measurements}")
    print(f"[SPRAWDZENIE] Dokumenty z pustą tablicą pomiarów (0 lub mniej): {empty_measurements}")
    
    # 2. Czyszczenie danych (Data Cleaning) - usuwanie dokumentów niespełniających wymogów poprawności
    query_invalid = {
        "$or": [
            {"measurements_count": {"$lte": 0}},
            {"measurements": {"$exists": False}},
            {"metadata": {"$exists": False}}
        ]
    }
    
    deleted_result = collection.delete_many(query_invalid)
    deleted_count = deleted_result.deleted_count
    
    if deleted_count > 0:
        print(f"[CZYSZCZENIE] Usunięto {deleted_count} wadliwych/pustych dokumentów.")
    else:
        print("[CZYSZCZENIE] Brak wadliwych dokumentów do usunięcia. Baza jest w pełni czysta.")
        
    # 3. Normalizacja danych – upewnienie się, że kluczowe metadane mają bezpieczne wartości domyślne
    updated_result = collection.update_many(
        {"metadata.Star_name": {"$exists": False}},
        {"$set": {"metadata.Star_name": "Unknown_Star"}}
    )
    if updated_result.modified_count > 0:
        print(f"[NORMALIZACJA] Uzupełniono brakujące nazwy gwiazd dla {updated_result.modified_count} dokumentów.")

    total_after = collection.count_documents({})
    print(f"[STAN PO] Łączna liczba poprawnych dokumentów po procesie czyszczenia: {total_after}")
    print("=" * 60)
    print("[SUKCES] Sprawdzanie i czyszczenie danych zakończone pomyślnie!\n")

if __name__ == "__main__":
    audit_and_clean_data()