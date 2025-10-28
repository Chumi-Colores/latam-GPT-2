import requests
from datetime import datetime

countries_to_nationalities_dictionary = {
    "Aruba": "aruban",
    "Bahamas": "bahamian",
    "Cuba": "cuban",
    "Jamaica": "jamaican",
    "Barbados": "barbadian",
    "Bermuda": "bermudian",
    "Bonaire": "bonairean",
    "Cayman Islands": "caymanian",
    "Curacao": "curacaoan",
    "Dominican Republic": "dominican",
    "Grenada": "grenadian",
    "Guadeloupe": "guadeloupean",
    "Haiti": "haitian",
    "Martinique": "martiniquais",
    "Montserrat": "montserratian",
    "Puerto Rico": "puerto_rican",
    "Trinidad and Tobago": "trinidadian_and_tobagonian",
    "Mexico": "mexican",
    "Belize": "belizean",
    "Guatemala": "guatemalan",
    "El Salvador": "salvadoran",
    "Honduras": "honduran",
    "Nicaragua": "nicaraguan",
    "Costa Rica": "costarican",
    "Panama": "panamanian"
}

# these were tested by hand
countries_that_do_not_work = ["Aruba", "Bahamas", "Belize", "Bermuda", "Bonaire", "Cayman Islands", "Curacao", "Grenada", 
                              "Guadeloupe", "Martinique", "Montserrat", "Trinidad and Tobago", "Costa Rica", "Haiti"]
# Haiti is out because they speak French/Creole there
countries_that_work = ["Cuba", "Mexico", "Jamaica", "Barbados", "Dominican Republic", "Puerto Rico", "Guatemala", 
                       "El Salvador", "Honduras", "Nicaragua", "Panama"]

languages_abreviations = {
    "eng" : "English",
    "spa" : "Spanish",
    "fre" : "French",
    "ger" : "German",
    "ita" : "Italian",
    "por" : "Portuguese",
    "dut" : "Dutch",
    "pol" : "Polish",
    "mul" : "Multiple Languages",
    "rus" : "Russian",
    "jpn" : "Japanese",
    "chi" : "Chinese",
    "lat" : "Latin",
    "heb": "Hebrew",
    "ara": "Arabic",
    "und" : "Undetermined",
    "nor" : "Norwegian",
    "swe" : "Swedish",
    "gre" : "Greek",
    "tur" : "Turkish",
    "cat" : "Catalan",
    "fin" : "Finnish",
    "dan" : "Danish",
    "hun" : "Hungarian",
    "ces" : "Czech",
    "ron" : "Romanian",
    "yor" : "Yoruba",
    "wel" : "Welsh",
    "ice" : "Icelandic",
    "kon" : "Kongo",
    "kir" : "Kirghiz",
    "glg" : "Galician",
    "lav" : "Latvian",
    "slv" : "Slovenian",
    "oci" : "Occitan",
    "myn" : "Mayan",
    "cpf" : "Creole French",
    "tuk" : "Turkmen",
    "sqi" : "Albanian",
    "ukr" : "Ukrainian",
    "amh" : "Amharic",
    "gle" : "Irish",
    "epo" : "Esperanto",
    "slo" : "Slovak",
    "cmn" : "Mandarin Chinese",
    "bul" : "Bulgarian",
    "srp" : "Serbian",
    "nob" : "Norwegian Bokmål",
    "hrv" : "Croatian",
    "rum" : "Romanian",
    "mal" : "Malayalam",
    "ben" : "Bengali",
    "arm" : "Armenian",
    "lit" : "Lithuanian",
    "tel" : "Telugu",
    "per" : "Persian",
    "vie" : "Vietnamese",
    "sin" : "Sinhala",
    "nah" : "Nahuatl",
    "tgl" : "Tagalog",
    "fil" : "Filipino",
    "cai" : "Central American Indian languages",
    "zap" : "Zapotec",
    "oto" : "Otomian languages",
    "cze" : "Czech",
    "yid" : "Yiddish",
    "gem" : "Germanic languages",
    "swa" : "Swahili",
    "guj" : "Gujarati",
    "grc" : "Ancient Greek",
    "urd" : "Urdu",
    "pan" : "Punjabi",
    "frm" : "Middle French",
    "gmh" : "Middle High German",
    "mga" : "Middle Irish",
    "mac" : "Macedonian",
    "kor" : "Korean",
    "fro" : "Old French",
    "ast" : "Asturian",
    "baq" : "Basque",
    "roa" : "Romance languages",
    "sai" : "South American Indian languages",
    "alb" : "Albanian",
    "som" : "Somali",
    "tam" : "Tamil",
    "pus" : "Pushto",
    "pro" : "Provençal",
    "uzb" : "Uzbek"
}

def get_authors_from_country(nationality, limit=1000) -> dict:
    url = f"https://openlibrary.org/subjects/{nationality}_authors.json"
    params = {"limit": limit}

    resp = requests.get(url, params=params, timeout=10)
    try:
        resp.raise_for_status()   # lanza HTTPError si status >= 400
    except requests.HTTPError as e:
        print(f"Error fetching authors for {nationality}: {e}")
        return {}
    data = resp.json()
    # get authors and their keys
    works = data.get("works", [])

    authors_dict = {}
    for work in works:
        authors = work.get("authors", [])
        if not authors:
            continue
        author = work.get("authors", [])[0]  # take the first author
        author_key = author.get("key").split("/")[-1]
        author_name = author.get("name")
        authors_dict[author_key] = {"name": author_name, "nationality": nationality}

    return authors_dict

def get_works_info_from_author(author_name, limit=200):
    works = {}
    url = f"https://openlibrary.org/search.json?author={author_name}"
    params = {"limit": limit}
    resp = requests.get(url, params=params)
    data = resp.json()
    works_list = data.get("docs", [])
    already_checked_works = set()
    for work in works_list:
        work_name = work.get("title")
        if work_name in already_checked_works:
            continue
        already_checked_works.add(work_name)
        work_id = work.get("key").split("/")[-1]
        # search for isbn from work_id
        if work_id[-1] == 'M':  # skip editions
            continue
        url = f"https://openlibrary.org/works/{work_id}/editions.json"
        resp = requests.get(url)
        data = resp.json()
        entries = data.get("entries", [])
        subjects = entries[0].get("subjects", []) if entries else []
        publish_date = parse_fecha(entries[0].get("publish_date", "")) if entries else None
        works[work_id] = {"title": work.get("title"), "authors": [author_name], "editions": [], "publish_date": publish_date, "subjects": subjects}

        print(work_id)
        for entry in entries:
            new_publish_date = parse_fecha(entry.get("publish_date", ""))
            if new_publish_date and (not works[work_id]["publish_date"] or new_publish_date < works[work_id]["publish_date"]):
                works[work_id]["publish_date"] = new_publish_date
            # add to isbns list without duplicates
            # look for isbn_13 or isbn_10
            isbn_13 = entry.get("isbn_13", [])
            isbn_10 = entry.get("isbn_10", [])
            isbn = ""
            if isbn_13:
                isbn = isbn_13[0]
            elif isbn_10:
                isbn = isbn_10[0]
        
            languages_aux = entry.get("languages", [])
            languages = [languages_abreviations[lang.get("key", "").split("/")[-1]] for lang in languages_aux]

            edition_info = { "isbn": isbn, "publishers": entry.get("publishers", []), "languages": languages}
            works[work_id]["editions"].append(edition_info)

    return works

def parse_fecha(fecha_str):
    formatos = [
        "%B %d, %Y",  # ej. April 25, 2007
        "%B %Y",       # ej. December 2000
        "%Y",          # ej. 1999
    ]
    for fmt in formatos:
        try:
            return datetime.strptime(fecha_str, fmt)
        except ValueError:
            continue
    return None
