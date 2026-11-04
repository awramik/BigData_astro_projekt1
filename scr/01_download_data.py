import os
import subprocess
import time

# Wyznaczanie ścieżek względem pliku skryptu
script_dir = os.path.dirname(os.path.abspath(__file__))
bat_file_path = os.path.join(script_dir, "..", "data", "wget_OPTICAL_CPS.bat")
output_dir = os.path.join(script_dir, "..", "data", "nasa_spectra")

os.makedirs(output_dir, exist_ok=True)

if not os.path.exists(bat_file_path):
    print(f"[BŁĄD] Nie widzę pliku w: {os.path.abspath(bat_file_path)}")
else:
    print(f"[SUKCES] Znaleziono plik źródłowy NASA! Analizuję zawartość...")
    with open(bat_file_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    downloads = []
    for line in lines:
        if "wget" in line and "http" in line:
            parts = line.strip().split()
            try:
                o_index = parts.index("-O")
                filename = parts[o_index + 1]
                
                raw_url = [p for p in parts if p.startswith("http")][0]
                url = raw_url.replace("http://", "https://").replace(":80", "")
                
                downloads.append((filename, url))
            except (ValueError, IndexError):
                continue

    print(f"Znaleziono łącznie {len(downloads)} zadań pobierania w oryginalnym pliku.")
    
    target_downloads = downloads[:500]
    print(f"Pobieram próbkę {len(target_downloads)} plików przez curl...")

    for i, (filename, url) in enumerate(target_downloads):
        dest_path = os.path.join(output_dir, filename)
        
        if not os.path.exists(dest_path) or os.path.getsize(dest_path) < 500:
            print(f"[{i+1}/{len(target_downloads)}] Pobieranie: {filename}")
            try:
                result = subprocess.run(
                    [
                        "curl", 
                        "-s", 
                        "-S",
                        "-L", 
                        "--http1.1", 
                        "--tlsv1.2",
                        "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", 
                        "-o", dest_path, 
                        url
                    ], 
                    capture_output=True, 
                    text=True,
                    timeout=30
                )
                if result.returncode != 0:
                    print(f"Błąd curl dla {filename}: {result.stderr.strip()}")
                
                time.sleep(0.5)
            except Exception as e:
                print(f"Błąd wywołania dla {filename}: {e}")
        else:
            print(f"[{i+1}/{len(target_downloads)}] Pominięto (już pobrany): {filename}")

    total_size_mb = sum(os.path.getsize(os.path.join(output_dir, f)) for f in os.listdir(output_dir) if os.path.isfile(os.path.join(output_dir, f))) / (1024 * 1024)
    print(f"\n[SUKCES] Pobieranie zakończone! Łączny rozmiar danych w folderze: {total_size_mb:.2f} MB.")