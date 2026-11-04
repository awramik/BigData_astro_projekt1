import os
from pymongo import MongoClient

# Połączenie z lokalną bazą MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["nasa_spectra_db"]
collection = db["spectra"]

def section_header(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

# ==========================================
# FILAR 1: STATYSTYKI TECHNICZNE I BAZODANOWE (Big Data / MongoDB)
# ==========================================

def analysis_db_1_collection_storage_stats():
    """
    ANALIZA TECH 1: Audyt pamięci masowej i rozmiaru kolekcji w MongoDB.
    Ocenia narzut danych, średni rozmiar dokumentu oraz strukturę fizyczną bazy.
    """
    section_header("TECH 1: Audyt architektury i pamięci masowej bazy MongoDB")
    
    stats = db.command("collStats", "spectra")
    total_size_mb = stats.get("size", 0) / (1024 * 1024)
    storage_size_mb = stats.get("storageSize", 0) / (1024 * 1024)
    avg_obj_size_kb = stats.get("avgObjSize", 0) / 1024
    
    print(f"-> Łączna liczba dokumentów w kolekcji: {stats.get('count', 0):,}")
    print(f"-> Czysty rozmiar danych w bazie: {total_size_mb:.2f} MB")
    print(f"-> Rzeczywisty rozmiar zajmowany na dysku (storage): {storage_size_mb:.2f} MB")
    print(f"-> Średni rozmiar pojedynczego dokumentu spektroskopowego: {avg_obj_size_kb:.2f} KB")
    print(f"-> Liczba aktywnych indeksów bazy danych: {stats.get('nindexes', 0)}")

def analysis_db_2_document_density_metrics():
    """
    ANALIZA TECH 2: Gęstość i zakres punktów pomiarowych w dokumentach.
    Analizuje rozkład liczby pomiarów i rzędów echelle per plik.
    """
    section_header("TECH 2: Analiza gęstości danych i rozdzielczości optycznej")
    
    pipeline = [
        {"$group": {
            "_id": None,
            "avg_points": {"$avg": "$measurements_count"},
            "max_points": {"$max": "$measurements_count"},
            "min_points": {"$min": "$measurements_count"},
            "total_points_in_db": {"$sum": "$measurements_count"}
        }}
    ]
    
    res = list(collection.aggregate(pipeline))[0]
    print(f"-> Łączna suma punktów pomiarowych we wszystkich dokumentach: {res['total_points_in_db']:,}")
    print(f"-> Średnia liczba wierszy pomiarowych na widmo: {res['avg_points']:,.1f}")
    print(f"-> Maksymalna gęstość widma w pliku: {res['max_points']:,}")
    print(f"-> Minimalna gęstość widma w pliku: {res['min_points']:,}")

def analysis_db_3_data_quality_null_matrix():
    """
    ANALIZA TECH 3: Macierz kompletności danych i współczynnik Null (Data Quality).
    """
    section_header("TECH 3: Audyt jakościowy i współczynnik wartości Null w bazie")
    
    pipeline = [
        {"$unwind": "$measurements"},
        {"$group": {
            "_id": None,
            "total_measurements": {"$sum": 1},
            "null_flux": {"$sum": {"$cond": [{"$eq": ["$measurements.Flux", None]}, 1, 0]}},
            "null_uncertainty": {"$sum": {"$cond": [{"$eq": ["$measurements.Flux_Uncertainty", None]}, 1, 0]}},
            "null_order": {"$sum": {"$cond": [{"$eq": ["$measurements.Order", None]}, 1, 0]}}
        }}
    ]
    
    res = list(collection.aggregate(pipeline, allowDiskUse=True))[0]
    total = res['total_measurements']
    
    print(f"-> Przeanalizowanych rekordów pomiarowych: {total:,}")
    print(f"-> Brak danych w polu 'Flux': {res['null_flux']:,} ({(res['null_flux']/total)*100:.2f}%)")
    print(f"-> Brak danych w polu 'Flux_Uncertainty': {res['null_uncertainty']:,} ({(res['null_uncertainty']/total)*100:.2f}%)")
    print(f"-> Brak danych w polu 'Order': {res['null_order']:,} ({(res['null_order']/total)*100:.2f}%)")


# ==========================================
# FILAR 2: STATYSTYKI NAUKOWE I ASTROFIZYCZNE (Cel badawczy projektu)
# ==========================================

def analysis_astro_1_kinematics_distribution():
    """
    ANALIZA SCI 1: Kinematyka układów gwiezdnych (Analiza prędkości barycentrycznej).
    Realizuje cel badawczy dotyczący właściwości kinematycznych.
    """
    section_header("SCI 1: Kinematyka katalogu – Rozkład prędkości radialnych (Barycentric Velocity)")
    
    pipeline = [
        {"$match": {"metadata.Barycentric_velocity_(m/s)": {"$exists": True}}},
        {"$project": {
            "star_name": "$metadata.Star_name",
            "telescope": "$metadata.Telescope",
            "velocity": {"$toDouble": "$metadata.Barycentric_velocity_(m/s)"}
        }},
        {"$group": {
            "_id": None,
            "avg_vel": {"$avg": "$velocity"},
            "max_vel": {"$max": "$velocity"},
            "min_vel": {"$min": "$velocity"},
            "std_vel": {"$stdDevPop": "$velocity"},
            "count": {"$sum": 1}
        }}
    ]
    
    res = list(collection.aggregate(pipeline))[0]
    print(f"-> Liczba zbadanych układów gwiezdnych pod kątem kinematyki: {res['count']}")
    print(f"-> Średnia prędkość barycentryczna populacji: {res['avg_vel']:.2f} m/s")
    print(f"-> Ekstrema prędkości w katalogu: Min = {res['min_vel']:.2f} m/s | Max = {res['max_vel']:.2f} m/s")
    print(f"-> Odchylenie standardowe prędkości (dyspersja kinematyczna): {res['std_vel']:.2f} m/s")

def analysis_astro_2_flux_intensity_extremes():
    """
    ANALIZA SCI 2: Ekstrema strumienia światła (Flux) – identyfikacja najjaśniejszych widm.
    Korelacja jasności i aktywności optycznej badanych gwiazd.
    """
    section_header("SCI 2: Analiza spektroskopowa – Globalne ekstrema strumienia (Flux)")
    
    pipeline = [
        {"$unwind": "$measurements"},
        {"$match": {"measurements.Flux": {"$ne": None}}},
        {"$group": {
            "_id": "$filename",
            "star_name": {"$first": "$metadata.Star_name"},
            "telescope": {"$first": "$metadata.Telescope"},
            "avg_flux": {"$avg": "$measurements.Flux"},
            "max_flux": {"$max": "$measurements.Flux"}
        }},
        {"$sort": {"max_flux": -1}},
        {"$limit": 3}
    ]
    
    results = list(collection.aggregate(pipeline, allowDiskUse=True))
    for i, r in enumerate(results, 1):
        print(f"{i}. Gwiazda: {r.get('star_name')} | Teleskop: {r.get('telescope')}")
        print(f"   Plik: {r['_id']} | Średni Flux: {r['avg_flux']:.2f} | Maksymalny Flux: {r['max_flux']:,}")

def analysis_astro_3_instrumental_setup_correlation():
    """
    ANALIZA SCI 3: Zależność konfiguracji optycznej (Spectral Resolution) od instrumentu.
    Pozwala ocenić jednorodność danych pod kątem aparatury pomiarowej (Keck/Hires).
    """
    section_header("SCI 3: Korelacja parametrów obserwacyjnych (Rozdzielczość vs Teleskop)")
    
    pipeline = [
        {"$match": {"metadata.Average_Spectral_Resolution": {"$exists": True}}},
        {"$group": {
            "_id": "$metadata.Telescope",
            "count": {"$sum": 1},
            "avg_resolution": {"$avg": {"$toDouble": "$metadata.Average_Spectral_Resolution"}}
        }}
    ]
    
    results = list(collection.aggregate(pipeline))
    for r in results:
        print(f"-> Teleskop / Aparatura: {r['_id']}")
        print(f"   Liczba widm w podzbiorze: {r['count']}")
        print(f"   Średnia rozdzielczość spektralna (R): {r['avg_resolution']:,.1f}")


def main():
    print("[URUCHOMIENIE] Rozpoczynam wielowymiarowy audyt i analizę Big Data...")
    
    # Wykonanie obu filarów
    analysis_db_1_collection_storage_stats()
    analysis_db_2_document_density_metrics()
    analysis_db_3_data_quality_null_matrix()
    
    analysis_astro_1_kinematics_distribution()
    analysis_astro_2_flux_intensity_extremes()
    analysis_astro_3_instrumental_setup_correlation()
    
    print("\n" + "=" * 70)
    print("[SUKCES] Wszystkie 6 analiz (techniczne i astrofizyczne) zakończone!")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    main()