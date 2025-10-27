import requests

BASE_URL = "https://openlibrary.org"

def get_author_key(author_name):
    """
    Obtener key del autor
    """

    response = requests.get(f"{BASE_URL}/search/authors.json", params={"q": author_name})
    data = response.json()

    if data["numFound"] > 0:
        return data["docs"][0]["key"].split("/")[-1]
    else:
        return None


def get_author_works(author_key):
    """
    Obtener trabajos
    """
    response = requests.get(f"{BASE_URL}/authors/{author_key}/works.json")
    data = response.json()
    return data.get("entries", [])


def get_editions_for_work(work_key):
    """
    Obtener editoriales y filtrar ediciones en otros idiomas
    """
    response = requests.get(f"{BASE_URL}/{work_key}/editions.json", params={"limit":100})
    data = response.json()

    editions = list()
        

    for entry in data.get("entries", []):
        spanish_found = False
        
        for language in entry.get("languages", []):
            if language["key"] == '/languages/spa':
                spanish_found = True
                break
        
        if not spanish_found:
            return None
        
        
        isbn = None
        #Checkear identificacion por isbn        
        if "isbn_13" in entry:                
            isbn = entry["isbn_13"][0]
        
        
        else:
            continue

        response = requests.get(f"{BASE_URL}/isbn/{isbn}.json")
        response.json()
        
        if "publishers" in response.json():
            pub = response.json()["publishers"][0]
        else:
            continue
        
        editions.append((pub, isbn))

    return list(editions)

def build_triplets_for_author(author_name, nationality):

    
    triplets = []
    
    author_key = get_author_key(author_name)

    if author_key:
        triplets.append([author_name, "es de nacionalidad", nationality])
        
        works = get_author_works(author_key)

        for work in works:
            title = work.get("title", "Unknown title")
            work_key = work["key"]  
            # (editorial, isbn)
            editions = get_editions_for_work(work_key)
            if not editions:
                continue

            triplets.append([author_name, "es autor de la obra", title])
            for edition in editions:
                publisher = edition[0]
                isbn = edition[1]
                
                triplets.append([isbn, "es un codigo ISBN para el libro", title])
                triplets.append([isbn, "es un codigo ISBN de una edicion publicada por", publisher])
                
    return triplets


def get_earliest_edition_for_work(work_key):
    response = requests.get(f"{BASE_URL}/{work_key}/editions.json", params={"limit":100})
    data = response.json()
    earliest_entry = None
    earliest_year = 100000
    for entry in data.get("entries", []):
        
        date = entry.get("publish_date", None)
        if date:
            import re
            year_match = re.search(r'\b(1[0-9]{3}|2[0-9]{3})\b', date)
            if year_match:
                year = int(year_match.group())
            else:
                continue
            
            
            if year < earliest_year:
                earliest_year = year
                earliest_entry = entry
    
    if not earliest_entry:
        return None
    
    subjects = earliest_entry.get("subjects", [])
    
    return (earliest_year, subjects)

def build_publication_date_and_category_triplets(author_name, known_titles_for_author):
    "Obtener fechas y categorias para obras del autor ya obtenidas"
    
    triplets = []
    
    author_key = get_author_key(author_name)

    if author_key:        
        works = get_author_works(author_key)

        for work in works:
            title = work.get("title", "NONE")
            
            if title not in known_titles_for_author:
                continue
            
            
            work_key = work["key"]  
            # (año, categorias)
            edition = get_earliest_edition_for_work(work_key)
            if not edition:
                continue
            year = edition[0]
            subjects = edition[1]
            
            triplets.append([title, "fue publicada en el año", str(year)])
            for subject in subjects:
                triplets.append([title, "pertenece a la categoria", subject])


            
                
    return triplets
