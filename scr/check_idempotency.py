import os
import glob
from pymongo import MongoClient

# Ścieżka do folderu z plikami
script_dir = os.path.dirname(os.path.abspath(__file__))
spectra_dir = os.path.join(script_dir, "..", "data", "nasa_spectra")

# Połączenie z bazą
client = MongoClient("mongodb://localhost:27017/")
db = client["nasa_spectra_db"]
collection = db["spectra"]

# Pobieramy set nazw plików już zapisanych w bazie
existing_filenames = set(collection.distinct("filename"))

# Pobieramy listę plików z dysku
local_files = [os.path.basename(f) for f in glob.glob(os.path.join(spectra_dir, "*.ipac"))]

# Szukamy różnicy (pliki na dysku, których nie ma w bazie)
new_files = [f for f in local_files if f not in existing_filenames]

print("=" * 50)
print(f"Liczba plików w folderze lokalnym: {len(local_files)}")
print(f"Liczba dokumentów w bazie MongoDB: {len(existing_filenames)}")
print(f"Liczba nowych plików do zaimportowania: {len(new_files)}")
print("=" * 50)

if new_files:
    print("Nowe pliki, które zostaną zaimportowane do bazy danych:")
    for nf in new_files:
        print(f"  -> {nf}")
else:
    print("Brak nowych plików. Baza danych jest aktualna względem folderu lokalnego.")