import os
from pymongo import MongoClient
import matplotlib.pyplot as plt

# Połączenie z bazą MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["nasa_spectra_db"]
collection = db["spectra"]

# Ustawienie stylu wykresów na profesjonalny
plt.style.use('seaborn-v0_8-darkgrid' if 'seaborn-v0_8-darkgrid' in plt.style.available else 'default')

def plot_1_velocity_distribution():
    """
    WIZUALIZACJA 1: Rozkład prędkości barycentrycznej (Kinematyka katalogu).
    """
    print("[1/3] Generowanie wykresu rozkładu prędkości barycentrycznej...")
    
    pipeline = [
        {"$match": {"metadata.Barycentric_velocity_(m/s)": {"$exists": True}}},
        {"$project": {
            "star_name": "$metadata.Star_name",
            "velocity": {"$toDouble": "$metadata.Barycentric_velocity_(m/s)"}
        }}
    ]
    
    data = list(collection.aggregate(pipeline))
    if not data:
        print("[OSTRZEŻENIE] Brak danych prędkości do wykresu 1.")
        return
        
    velocities = [d["velocity"] for d in data]
    mean_vel = sum(velocities) / len(velocities)
    
    plt.figure(figsize=(10, 6))
    n, bins, patches = plt.hist(velocities, bins=25, color='#2b5c8f', edgecolor='black', alpha=0.85)
    
    # Dodanie linii średniej populacji
    plt.axvline(mean_vel, color='crimson', linestyle='--', linewidth=2, label=f'Średnia: {mean_vel:.1f} m/s')
    
    plt.title("Rozkład prędkości barycentrycznej badanych układów gwiezdnych", fontsize=13, fontweight='bold', pad=15)
    plt.xlabel("Prędkość Barycentryczna [m/s]", fontsize=11)
    plt.ylabel("Liczba obiektów (Częstotliwość)", fontsize=11)
    plt.legend(fontsize=11)
    plt.grid(True, linestyle='--', alpha=0.6)
    
    output_path = os.path.join(os.path.dirname(__file__), "..", "data", "chart_1_velocity_distribution.png")
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"   -> Zapisano: {output_path}")

def plot_2_top_flux_stars():
    """
    WIZUALIZACJA 2: Ranking najjaśniejszych gwiazd (Maksymalny Flux).
    """
    print("[2/3] Generowanie wykresu ekstremów strumienia optycznego...")
    
    pipeline = [
        {"$unwind": "$measurements"},
        {"$match": {"measurements.Flux": {"$ne": None}}},
        {"$group": {
            "_id": "$metadata.Star_name",
            "max_flux": {"$max": "$measurements.Flux"},
            "avg_flux": {"$avg": "$measurements.Flux"}
        }},
        {"$sort": {"max_flux": -1}},
        {"$limit": 5}
    ]
    
    data = list(collection.aggregate(pipeline, allowDiskUse=True))
    if not data:
        print("[OSTRZEŻENIE] Brak danych do wykresu 2.")
        return
        
    stars = [d["_id"] if d["_id"] else "Unknown" for d in data]
    max_fluxes = [d["max_flux"] for d in data]
    
    plt.figure(figsize=(10, 6))
    bars = plt.barh(stars[::-1], max_fluxes[::-1], color='#e67e22', edgecolor='black', alpha=0.9)
    
    plt.title("Top 5 obiektów o najwyższym maksymalnym strumieniu (Flux)", fontsize=13, fontweight='bold', pad=15)
    plt.xlabel("Maksymalny Strumień optyczny [jednostki względne]", fontsize=11)
    plt.ylabel("Nazwa Gwiazdy", fontsize=11)
    plt.grid(True, axis='x', linestyle='--', alpha=0.6)
    
    output_path = os.path.join(os.path.dirname(__file__), "..", "data", "chart_2_top_flux_stars.png")
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"   -> Zapisano: {output_path}")

def plot_3_sample_stellar_spectrum():
    """
    WIZUALIZACJA 3: Fizyczne widmo optyczne wybranej gwiazdy (Wavelength vs Flux).
    Pobiera pełne widmo z jednego dokumentu z bazy i rysuje krzywą spektroskopową.
    """
    print("[3/3] Generowanie wykresu widma optycznego (Wavelength vs Flux)...")
    
    # Pobieramy jeden bogaty dokument spektroskopowy z bazy
    doc = collection.find_one({"measurements_count": {"$gt": 100000}})
    if not doc:
        doc = collection.find_one() # Awaryjnie pierwszy lepszy
        
    if not doc or "measurements" not in doc:
        print("[OSTRZEŻENIE] Nie znaleziono danych do wykresu widma.")
        return
        
    star_name = doc.get("metadata", {}).get("Star_name", "Nieznana")
    filename = doc.get("filename", "plik")
    
    measurements = doc["measurements"]
    
    # Wyciągamy długości fal i strumień (pomijając null)
    wavelengths = []
    fluxes = []
    for m in measurements:
        w = m.get("Wavelength")
        f = m.get("Flux")
        if w is not None and f is not None:
            wavelengths.append(w)
            fluxes.append(f)
            
    # Sortujemy po długości fali, żeby wykres był ciągły
    combined = sorted(zip(wavelengths, fluxes))
    wavelengths = [item[0] for item in combined]
    fluxes = [item[1] for item in combined]
    
    plt.figure(figsize=(12, 5))
    plt.plot(wavelengths, fluxes, color='#8e44ad', linewidth=0.6, alpha=0.9)
    
    plt.title(f"Widmo optyczne dla układu {star_name} (Plik: {filename})", fontsize=13, fontweight='bold', pad=15)
    plt.xlabel("Długość fali [mikrony]", fontsize=11)
    plt.ylabel("Strumień [Flux - Relative]", fontsize=11)
    plt.grid(True, linestyle='--', alpha=0.5)
    
    output_path = os.path.join(os.path.dirname(__file__), "..", "data", "chart_3_stellar_spectrum.png")
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"   -> Zapisano: {output_path}")

def main():
    print("=" * 60)
    print("--- [05_visualization.py] Rozpoczęcie generowania wykresów ---")
    print("=" * 60)
    
    plot_1_velocity_distribution()
    plot_2_top_flux_stars()
    plot_3_sample_stellar_spectrum()
    
    print("=" * 60)
    print("[SUKCES] Wszystkie 3 wykresy zostały wygenerowane i zapisane w folderze 'data/'!")
    print("=" * 60)

if __name__ == "__main__":
    main()