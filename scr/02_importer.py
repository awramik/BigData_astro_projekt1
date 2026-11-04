import os
import glob
from pymongo import MongoClient

# Konfiguracja ścieżek względem pliku skryptu
script_dir = os.path.dirname(os.path.abspath(__file__))
spectra_dir = os.path.join(script_dir, "..", "data", "nasa_spectra")

# Połączenie z lokalną bazą MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["nasa_spectra_db"]
collection = db["spectra"]

# [WYMAGANIE 4.0] Tworzenie unikalnego indeksu na polu "filename",
# co uniemożliwia fizyczne duplikaty dokumentów
collection.create_index("filename", unique=True)

def parse_ipac_file(file_path):
    """
    Parsuje plik spektroskopowy NASA w formacie IPAC,
    uwzględniając metadane, nagłówki tabeli oraz wartości null.
    """
    metadata = {}
    columns = []
    data_rows = []
    
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
        
    for line in lines:
        line_str = line.strip()
        if not line_str:
            continue
            
        # 1. Obsługa metadanych zaczynających się od '\'
        if line_str.startswith("\\"):
            if "=" in line_str:
                parts = line_str.lstrip("\\").split("=", 1)
                key = parts[0].strip()
                val = parts[1].strip().strip('"')
                metadata[key] = val
            continue
            
        # 2. Obsługa linii nagłówkowych tabeli (zaczynających się od '|')
        if line_str.startswith("|"):
            if not columns:
                columns = [c.strip() for c in line_str.split("|") if c.strip()]
            continue
            
        # 3. Wiersze danych (zwykłe linie numeryczne)
        if columns:
            parts = line_str.split()
            if len(parts) >= len(columns):
                row_dict = {}
                for col, val in zip(columns, parts[:len(columns)]):
                    if val.lower() == "null":
                        row_dict[col] = None
                        continue
                        
                    try:
                        if "." in val or "e" in val.lower():
                            row_dict[col] = float(val)
                        else:
                            row_dict[col] = int(val)
                    except ValueError:
                        row_dict[col] = val
                        
                data_rows.append(row_dict)
                
    return {
        "filename": os.path.basename(file_path),
        "metadata": metadata,
        "measurements_count": len(data_rows),
        "measurements": data_rows
    }

def main():
    ipac_files = glob.glob(os.path.join(spectra_dir, "*.ipac"))
    print(f"Znaleziono {len(ipac_files)} plików .ipac w folderze docelowym.")
    
    if not ipac_files:
        print("[OSTRZEŻENIE] Brak plików w folderze nasa_spectra. Należy pobrać dane!")
        return

    processed_count = 0
    for i, file_path in enumerate(ipac_files):
        filename = os.path.basename(file_path)
        
        try:
            parsed_data = parse_ipac_file(file_path)
            
            # [WYMAGANIE 4.0] Idempotentny zapis: update z upsert=True.
            # Jeśli dokument z tym "filename" już istnieje -> aktualizuje go.
            # Jeśli go nie ma -> tworzy nowy.
            result = collection.update_one(
                {"filename": filename},
                {"$set": parsed_data},
                upsert=True
            )
            
            processed_count += 1
            if result.upserted_id:
                status = "Dodano nowy"
            else:
                status = "Zaktualizowano (istniał)"
                
            print(f"[{i+1}/{len(ipac_files)}] {status}: {filename} ({parsed_data['measurements_count']} wierszy)")
            
        except Exception as e:
            print(f"Błąd przetwarzania pliku {filename}: {e}")

    print(f"\n[SUKCES] Import idempotentny zakończony! Przetworiono {processed_count} plików.")
    print(f"Łączna liczba dokumentów w kolekcji 'spectra': {collection.count_documents({})}")

if __name__ == "__main__":
    main()