#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dataset_eu_books_alllangs_v1.py
--------------------------------
- Incluye ediciones de *todos* los idiomas (no filtra por español).
- OMITE obras sin ISBN (requiere ≥1 ISBN en alguna edición).
- Paginación de ediciones por obra (limit/offset) configurable.
- Extrae ISBNs de la entrada y del detalle (/books/{edition}.json).
- Tripletas emitidas:
  1) (Autor, "es de nacionalidad", País)
  2) (Autor, "es autor de la obra", Título)            **solo si la obra tiene ≥1 ISBN**
  3) (ISBN, "es un codigo ISBN para el libro", Título)
  4) (ISBN, "es un codigo ISBN de una edicion publicada por", Editorial)
  5) (Título, "es del año", Año)                        **si aparece en alguna edición**
  6) (Título, "pertenece al género", Género)            **desde /works/{work}.json -> 'subjects'**
  7) (ISBN, "está escrito en", Idioma)                  **nuevo: por cada idioma detectado en la edición**

- Deduplicación fuerte y normalización de espacios.
- Fallback: si /authors/{OLID}/works.json no existe, busca por nombre en /search.json?author=

CSV columnas: subject, relation, object, source, country,
              author_wikidata_id, author_openlibrary_id,
              work_olid, edition_olid, isbn, language_source
"""

import argparse
import csv
import json
import logging
import re
import time
from typing import Dict, List, Optional, Tuple, Set
import os

import pandas as pd
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from tqdm import tqdm

WIKIDATA_SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
HEADERS = {"User-Agent": "EU-Books-Dataset/1.8 (academic use; contact: example@example.com)",
           "Accept": "application/sparql-results+json"}

OPENLIBRARY_BASE = "https://openlibrary.org"
OPENLIBRARY_HEADERS = {"User-Agent": "EU-Books-Dataset/1.8 (academic use; contact: example@example.com)"}

COUNTRY_QIDS: Dict[str, str] = {
    "United Kingdom": "Q145", "France": "Q142", "Germany": "Q183", "Italy": "Q38", "Spain": "Q29",
    "Portugal": "Q45", "Netherlands": "Q55", "Belgium": "Q31", "Sweden": "Q34", "Norway": "Q20",
    "Denmark": "Q35", "Finland": "Q33", "Ireland": "Q27", "Poland": "Q36", "Czech Republic": "Q213",
    "Austria": "Q40", "Switzerland": "Q39", "Greece": "Q41", "Hungary": "Q28", "Romania": "Q218",
    "Bulgaria": "Q219", "Serbia": "Q403", "Croatia": "Q224", "Slovenia": "Q215",
}

# Mapeo simple de códigos ISO 639-2/OL a nombres en español (comunes).
LANG_MAP = {
    "spa": "Español", "eng": "Inglés", "fre": "Francés", "fra": "Francés", "ger": "Alemán", "deu": "Alemán",
    "ita": "Italiano", "por": "Portugués", "cat": "Catalán", "glg": "Gallego", "eus": "Euskera",
    "dut": "Neerlandés", "nld": "Neerlandés", "swe": "Sueco", "nor": "Noruego", "dan": "Danés",
    "fin": "Finés", "pol": "Polaco", "ces": "Checo", "cze": "Checo", "ell": "Griego", "gre": "Griego",
    "rum": "Rumano", "ron": "Rumano", "hun": "Húngaro", "bul": "Búlgaro", "srp": "Serbio", "hrv": "Croata",
    "slv": "Esloveno", "gle": "Irlandés", "ice": "Islandés", "isl": "Islandés"
}

def normalize_space(s: Optional[str]) -> Optional[str]:
    if s is None: return s
    s = re.sub(r"\s+", " ", str(s))
    return s.strip()

def slug(s: str) -> str:
    return normalize_space(s or "").lower()

def year_from_publish_date(s: Optional[str]) -> Optional[str]:
    if not s: return None
    m = re.search(r"(17|18|19|20)\d{2}", s)
    return m.group(0) if m else None

def languages_from_entry_or_detail(entry: dict, detail: Optional[dict]) -> Tuple[List[str], str]:
    """
    Devuelve ([lista_de_idiomas_en_texto], source_tag)
    Revisa 'languages' (keys tipo '/languages/spa') y campos 'publish_language' o 'language'.
    """
    langs: List[str] = []
    src = "none"
    def _extract(obj):
        tmp = []
        if obj is None: 
            return tmp
        if isinstance(obj, list):
            for v in obj:
                if isinstance(v, dict) and "key" in v:
                    code = v["key"].split("/")[-1].strip().lower()
                    tmp.append(LANG_MAP.get(code, code))
                elif isinstance(v, str):
                    tmp.append(LANG_MAP.get(v.strip().lower(), v.strip()))
        elif isinstance(obj, dict) and "key" in obj:
            code = obj["key"].split("/")[-1].strip().lower()
            tmp.append(LANG_MAP.get(code, code))
        elif isinstance(obj, str):
            tmp.append(LANG_MAP.get(obj.strip().lower(), obj.strip()))
        return tmp

    l1 = _extract(entry.get("languages"))
    l2 = _extract(entry.get("publish_language") or entry.get("language"))
    if l1 or l2:
        langs.extend(l1 or [])
        langs.extend(l2 or [])
        src = "entry"
    # detalle
    if detail:
        l3 = _extract(detail.get("languages"))
        l4 = _extract(detail.get("publish_language") or detail.get("language"))
        if l3 or l4:
            langs.extend(l3 or [])
            langs.extend(l4 or [])
            src = "books_api"
    # normaliza + dedupe preservando orden
    langs = [normalize_space(x) for x in langs if x]
    seen = set()
    unique_langs = []
    for x in langs:
        if x not in seen:
            seen.add(x)
            unique_langs.append(x)
    return unique_langs, src

@retry(reraise=True, stop=stop_after_attempt(3),
       wait=wait_exponential(multiplier=1, min=1, max=8),
       retry=retry_if_exception_type((requests.exceptions.RequestException,)))
def http_get(url: str, params: Optional[Dict] = None, headers: Optional[Dict] = None, timeout: int = 30):
    resp = requests.get(url, params=params or {}, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp

def http_get_json(url: str, params: Optional[Dict] = None, headers: Optional[Dict] = None) -> dict:
    try:
        r = http_get(url, params=params, headers=headers)
        return r.json()
    except requests.exceptions.HTTPError as e:
        logging.warning(f"HTTP {e.response.status_code} en {url}. Se continúa si aplica.")
        return {}
    except (json.JSONDecodeError, requests.exceptions.RequestException) as e:
        logging.warning(f"Error al obtener {url}: {e}")
        return {}

def sparql_authors_by_country(country_qid: str, limit: int = 50) -> List[dict]:
    q = f"""
    SELECT DISTINCT ?author ?authorLabel ?openLibraryID WHERE {{
      ?author wdt:P31 wd:Q5 .
      ?author wdt:P27 wd:{country_qid} .
      ?author wdt:P106 ?occupation .
      VALUES ?occupation {{ wd:Q36180 wd:Q482980 }}
      OPTIONAL {{ ?author wdt:P648 ?openLibraryID. }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "es,en". }}
    }}
    LIMIT {limit}
    """
    data = http_get_json(WIKIDATA_SPARQL_ENDPOINT, params={"query": q, "format": "json"}, headers=HEADERS)
    out = []
    for b in data.get("results", {}).get("bindings", []):
        out.append({
            "wikidata_qid": b.get("author", {}).get("value", "").split("/")[-1],
            "name": b.get("authorLabel", {}).get("value", ""),
            "openlibrary_id": b.get("openLibraryID", {}).get("value", "") or None,
        })
    return out

def ol_search_author_works_by_name(author_name: str, limit: int = 20) -> List[dict]:
    data = http_get_json(f"{OPENLIBRARY_BASE}/search.json",
                         params={"author": author_name, "limit": limit},
                         headers=OPENLIBRARY_HEADERS)
    works = []
    for d in data.get("docs", []):
        title = d.get("title"); key = d.get("key")
        if title and key and key.startswith("/works/"):
            works.append({"title": title, "work_olid": key.split("/")[-1]})
    # dedupe
    uniq = {w["work_olid"]: w for w in works}
    return list(uniq.values())[:limit]

def ol_works_by_author_olid(author_olid: str, limit: int = 50) -> List[dict]:
    data = http_get_json(f"{OPENLIBRARY_BASE}/authors/{author_olid}/works.json",
                         headers=OPENLIBRARY_HEADERS, params={"limit": limit})
    entries = data.get("entries")
    if not isinstance(entries, list):
        return []
    works = []
    for e in entries:
        title = e.get("title"); key = e.get("key")
        if title and key:
            works.append({"title": title, "work_olid": key.split("/")[-1]})
    return works[:limit]

def fetch_edition_detail(edition_olid: str) -> dict:
    return http_get_json(f"{OPENLIBRARY_BASE}/books/{edition_olid}.json", headers=OPENLIBRARY_HEADERS)

def fetch_work_detail(work_olid: str) -> dict:
    return http_get_json(f"{OPENLIBRARY_BASE}/works/{work_olid}.json", headers=OPENLIBRARY_HEADERS)

def extract_isbns_from_entry_and_detail(entry: dict, detail: Optional[dict]) -> Set[str]:
    isbns: Set[str] = set()
    for k in ("isbn_13", "isbn_10"):
        vals = entry.get(k, [])
        if isinstance(vals, list):
            for v in vals:
                if v: isbns.add(str(v).strip())
        elif isinstance(vals, str):
            isbns.add(vals.strip())
    if detail:
        for k in ("isbn_13", "isbn_10"):
            vals = detail.get(k, [])
            if isinstance(vals, list):
                for v in vals:
                    if v: isbns.add(str(v).strip())
            elif isinstance(vals, str):
                isbns.add(vals.strip())
        identifiers = detail.get("identifiers", {})
        if isinstance(identifiers, dict):
            for key in ("isbn_13", "isbn_10"):
                vals = identifiers.get(key, [])
                if isinstance(vals, list):
                    for v in vals:
                        if v: isbns.add(str(v).strip())
                elif isinstance(vals, str):
                    isbns.add(vals.strip())
    # normalizar (quitar espacios/guiones)
    normed = set()
    for x in isbns:
        normed.add(re.sub(r"[\s-]", "", x))
    return normed

def triples_to_dataframe(triples: List[dict]) -> pd.DataFrame:
    if not triples:
        return pd.DataFrame(columns=[
            "subject","relation","object","source","country",
            "author_wikidata_id","author_openlibrary_id","work_olid","edition_olid","isbn","language_source"
        ])
    df = pd.DataFrame(triples)
    for col in ("subject","relation","object","country","source"):
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
    keep_cols = ["subject","relation","object","country","source"]
    df = df.drop_duplicates(subset=[c for c in keep_cols if c in df.columns]).reset_index(drop=True)
    return df

def build_triples_for_country(country_name: str, country_qid: str,
                              authors_per_country: int, works_per_author: int,
                              editions_per_work: int, page_size: int, max_pages: int,
                              sleep: float = 0.8) -> List[dict]:
    triples: List[dict] = []
    authors = sparql_authors_by_country(country_qid, limit=authors_per_country)
    time.sleep(sleep)

    for a in tqdm(authors, desc=f"Autores de {country_name}"):
        author_name = normalize_space(a.get("name") or "Autor Desconocido")
        author_qid = a.get("wikidata_qid")
        author_olid = a.get("openlibrary_id")

        # Tripleta de nacionalidad
        triples.append({
            "subject": author_name,
            "relation": "es de nacionalidad",
            "object": country_name,
            "source": "Wikidata",
            "country": country_name,
            "author_wikidata_id": author_qid,
            "author_openlibrary_id": author_olid,
            "work_olid": None,
            "edition_olid": None,
            "isbn": None,
            "language_source": None
        })

        # Works (prefer OLID, fallback nombre)
        if author_olid:
            works = ol_works_by_author_olid(author_olid, limit=works_per_author)
            time.sleep(sleep)
            if not works:
                works = ol_search_author_works_by_name(author_name, limit=works_per_author)
                time.sleep(sleep)
        else:
            works = ol_search_author_works_by_name(author_name, limit=works_per_author)
            time.sleep(sleep)

        for w in works:
            title = normalize_space(w.get("title") or "Obra Desconocida")
            work_olid = w.get("work_olid")
            if not work_olid:
                continue

            collected_isbns: Set[str] = set()
            total_collected_editions = 0
            offset = 0
            pages_done = 0

            # dedup locales
            seen_isbn_title = set()
            seen_isbn_pub = set()
            seen_isbn_lang = set()

            while total_collected_editions < editions_per_work and pages_done < max_pages:
                data = http_get_json(f"{OPENLIBRARY_BASE}/works/{work_olid}/editions.json",
                                     headers=OPENLIBRARY_HEADERS,
                                     params={"limit": page_size, "offset": offset})
                entries = data.get("entries", [])
                if not entries:
                    break

                for ed in entries:
                    try:
                        edition_key = ed.get("key")
                        ed_olid = edition_key.split("/")[-1] if edition_key else None
                        detail = fetch_edition_detail(ed_olid) if ed_olid else None

                        # Año
                        year = year_from_publish_date(ed.get("publish_date"))

                        # Idiomas
                        langs, lang_src = languages_from_entry_or_detail(ed, detail)

                        # ISBNs (omite edición si no hay ISBN)
                        isbns = extract_isbns_from_entry_and_detail(ed, detail)
                        if not isbns:
                            continue

                        # Editorial(es)
                        pubs = ed.get("publishers", []) or []
                        if not pubs and detail:
                            pubs = detail.get("publishers", []) or []
                        pubs = [normalize_space(p) for p in pubs if p]
                        pubs = list(dict.fromkeys(pubs))

                        for isbn in isbns:
                            collected_isbns.add(isbn)

                            # (3) ISBN -> libro
                            key1 = (isbn, slug(title))
                            if key1 not in seen_isbn_title:
                                seen_isbn_title.add(key1)
                                triples.append({
                                    "subject": isbn,
                                    "relation": "es un codigo ISBN para el libro",
                                    "object": title,
                                    "source": "OpenLibrary",
                                    "country": country_name,
                                    "author_wikidata_id": author_qid,
                                    "author_openlibrary_id": author_olid,
                                    "work_olid": work_olid,
                                    "edition_olid": ed_olid,
                                    "isbn": isbn,
                                    "language_source": lang_src
                                })

                            # (4) ISBN -> editorial
                            for pub in sorted(pubs):
                                key2 = (isbn, slug(pub))
                                if key2 not in seen_isbn_pub:
                                    seen_isbn_pub.add(key2)
                                    triples.append({
                                        "subject": isbn,
                                        "relation": "es un codigo ISBN de una edicion publicada por",
                                        "object": pub,
                                        "source": "OpenLibrary",
                                        "country": country_name,
                                        "author_wikidata_id": author_qid,
                                        "author_openlibrary_id": author_olid,
                                        "work_olid": work_olid,
                                        "edition_olid": ed_olid,
                                        "isbn": isbn,
                                        "language_source": lang_src
                                    })

                            # (7) ISBN -> idioma(s)
                            for lang in langs or []:
                                key3 = (isbn, slug(lang))
                                if key3 not in seen_isbn_lang:
                                    seen_isbn_lang.add(key3)
                                    triples.append({
                                        "subject": isbn,
                                        "relation": "está escrito en",
                                        "object": lang,
                                        "source": "OpenLibrary",
                                        "country": country_name,
                                        "author_wikidata_id": author_qid,
                                        "author_openlibrary_id": author_olid,
                                        "work_olid": work_olid,
                                        "edition_olid": ed_olid,
                                        "isbn": isbn,
                                        "language_source": lang_src
                                    })

                        if year:
                            triples.append({
                                "subject": title,
                                "relation": "es del año",
                                "object": str(year),
                                "source": "OpenLibrary",
                                "country": country_name,
                                "author_wikidata_id": author_qid,
                                "author_openlibrary_id": author_olid,
                                "work_olid": work_olid,
                                "edition_olid": ed_olid,
                                "isbn": None,
                                "language_source": lang_src
                            })

                        total_collected_editions += 1
                        if total_collected_editions >= editions_per_work:
                            break
                    except Exception as e:
                        logging.warning(f"Edición saltada ({work_olid}): {e}")
                        continue

                pages_done += 1
                offset += page_size
                time.sleep(sleep)

            # Acepta obra solo si hubo ≥1 ISBN
            if not collected_isbns:
                continue

            # (2) autor -> obra
            triples.append({
                "subject": author_name,
                "relation": "es autor de la obra",
                "object": title,
                "source": "OpenLibrary",
                "country": country_name,
                "author_wikidata_id": author_qid,
                "author_openlibrary_id": author_olid,
                "work_olid": work_olid,
                "edition_olid": None,
                "isbn": None,
                "language_source": None
            })

            # (6) género(s) desde /works/{work}.json
            try:
                wdetail = fetch_work_detail(work_olid)
                subjects = wdetail.get("subjects", []) or []
                count_genres = 0
                for g in subjects:
                    g_norm = normalize_space(g)
                    if not g_norm:
                        continue
                    triples.append({
                        "subject": title,
                        "relation": "pertenece al género",
                        "object": g_norm,
                        "source": "OpenLibrary",
                        "country": country_name,
                        "author_wikidata_id": author_qid,
                        "author_openlibrary_id": author_olid,
                        "work_olid": work_olid,
                        "edition_olid": None,
                        "isbn": None,
                        "language_source": None
                    })
                    count_genres += 1
                    if count_genres >= 3:
                        break
            except Exception as e:
                logging.warning(f"No se pudo obtener género para {title}: {e}")

    return triples

def save_triples_csv(triples, out_path):
    import pandas as pd
    df = triples_to_dataframe(triples)
    # dedup fuerte por las columnas clave
    keep = [c for c in ["subject","relation","object","country","source"] if c in df.columns]
    df = df.drop_duplicates(subset=keep).reset_index(drop=True)
    # escritura atómica (tmp + rename)
    tmp = out_path + ".tmp"
    df.to_csv(tmp, index=False)
    os.replace(tmp, out_path)
    return len(df)

def main():
    parser = argparse.ArgumentParser(description="Dataset EU libros — TODOS LOS IDIOMAS, con idioma por ISBN.")
    parser.add_argument("--countries", type=str, required=True, help="Lista 'Spain,Germany,France,...'")
    parser.add_argument("--authors-per-country", type=int, default=25)
    parser.add_argument("--works-per-author", type=int, default=10)
    parser.add_argument("--editions-per-work", type=int, default=30)
    parser.add_argument("--page-size", type=int, default=50)
    parser.add_argument("--max-edition-pages", type=int, default=12)
    parser.add_argument("--sleep", type=float, default=0.9)
    parser.add_argument("--out", type=str, default="eu_books_triples_alllangs.csv")
    parser.add_argument("--out-dir", type=str, default="out_countries")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    os.makedirs(args.out_dir, exist_ok=True)
    summary = []
    countries = [normalize_space(c) for c in args.countries.split(",")]
    missing = [c for c in countries if c not in COUNTRY_QIDS]
    if missing:
        raise ValueError(f"Países no configurados: {missing}")

    all_triples: List[dict] = []
    for c in countries:
        qid = COUNTRY_QIDS[c]
        logging.info(f"Procesando país: {c} (QID {qid})")
        triples = build_triples_for_country(
            c, qid,
            authors_per_country=args.authors_per_country,
            works_per_author=args.works_per_author,
            editions_per_work=args.editions_per_work,
            page_size=args.page_size,
            max_pages=args.max_edition_pages,
            sleep=args.sleep
        )
        all_triples.extend(triples)

        out_country = os.path.join(args.out_dir, f"{slug(c)}.csv")
        n = save_triples_csv(triples, out_country)
        logging.info(f"[{c}] Guardadas {n} tripletas en {out_country}")
        summary.append((c, n))


    df = triples_to_dataframe(all_triples)
    df.to_csv(args.out, index=False, quoting=csv.QUOTE_MINIMAL, encoding="utf-8")
    logging.info(f"OK. Tripletas guardadas: {len(df)} en {args.out}")

if __name__ == "__main__":
    main()
