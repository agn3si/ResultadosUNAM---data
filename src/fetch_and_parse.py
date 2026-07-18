import re
import time
from pathlib import Path
from urllib.parse import urljoin
from curl_cffi import requests
import pandas as pd
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
    "Cache-Control": "max-age=0",
    "DNT": "1",
    "Priority": "u=0, i",
    "Sec-CH-UA": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "Sec-CH-UA-Mobile": "?0",
    "Sec-CH-UA-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

session = requests.Session(impersonate="chrome124")
session.headers.update(HEADERS)

ÁREAS = {1: "15.html", 2: "25.html", 3: "35.html", 4: "45.html"}
AÑOS = [2021, 2022, 2023, 2024, 2025, 2026]


def fetch(url: str, raw_dir: Path, cache_name: str, referer: str = None) -> str:
    raw_dir.mkdir(parents=True, exist_ok=True)
    cache_path = raw_dir / f"{cache_name}.html"
    if cache_path.exists():
        return cache_path.read_text(encoding="utf-8")
    extra = {"Sec-Fetch-Site": "none"}
    if referer:
        extra = {"Referer": referer, "Sec-Fetch-Site": "same-origin"}
    resp = session.get(url, headers=extra, timeout=15)
    resp.raise_for_status()
    cache_path.write_text(resp.text, encoding="utf-8")
    time.sleep(1.5)
    return resp.text


def parse_indice(html: str, base_url: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    entries = []
    for a in soup.find_all("a", href=True):
        if re.search(r"\d{8}\.html$", a["href"]):
            carrera_tag = a.find_previous("h3")
            carrera = carrera_tag.get_text(strip=True) if carrera_tag else "DESCONOCIDA"
            url = urljoin(base_url, a["href"])
            entries.append({"carrera": carrera, "plantel": a.get_text(strip=True), "url": url})
    return entries


def parse_carrera_page(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    full_text = soup.get_text(" ", strip=True)
    stats = dict(re.findall(r"([A-Za-zÁÉÍÓÚñ ]+?)\s*=\s*(\d+)", full_text))
    rows = []
    for tr in soup.find_all("tr"):
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if len(cells) >= 3 and re.fullmatch(r"\d{6}", cells[0]):
            rows.append({
                "folio": cells[0],
                "aciertos": int(cells[1]) if cells[1].isdigit() else None,
                "acreditado": cells[2] if cells[2] in ("S", "N", "C") else None,
            })
    return {"stats": stats, "rows": rows}


all_rows = []
for area_num, área_indice in ÁREAS.items():
    for año in AÑOS:
        raw_dir = Path(f"data/raw/{año}")
        indice_url = f"https://www.dgae.unam.mx/Licenciatura{año}/resultados/{área_indice}"
        indice_html = fetch(indice_url, raw_dir, f"indice_area{area_num}")
        entradas = parse_indice(indice_html, indice_url)
        print(f"\n=== área {area_num}, {año}: {len(entradas)} carrera-plantel ===")

        for entrada in entradas:
            codigo = re.search(r"(\d{8})\.html$", entrada["url"]).group(1)
            html = fetch(entrada["url"], raw_dir, codigo, referer=indice_url)
            resultado = parse_carrera_page(html)
            for r in resultado["rows"]:
                r["año"] = año
                r["area"] = area_num
                r["carrera"] = entrada["carrera"]
                r["plantel"] = entrada["plantel"]
                all_rows.append(r)

df = pd.DataFrame(all_rows)
Path("data/processed").mkdir(parents=True, exist_ok=True)
df.to_csv(f"data/processed/aciertos_unam_{min(AÑOS)}_{max(AÑOS)}.csv", index=False)
print(f"\nGuardado data/processed/aciertos_unam_{min(AÑOS)}_{max(AÑOS)}.csv con {len(df)} filas totales")