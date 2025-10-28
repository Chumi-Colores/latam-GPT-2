import os
from utils import nationalities_to_countries_dictionary
import csv

def make_author_nationality_triplets():
    path = os.path.join("centroamerica", "authors_nationalities.csv")
    rows = []
    with open(path, mode='r', encoding='utf-8') as file:
        lector = csv.reader(file)
        next(lector)
        for row in lector:
            rows.append([row[0], "es_de", nationalities_to_countries_dictionary.get(row[1], "Desconocido")])
    
    with open(os.path.join("centroamerica", "authors_nationalities_triplets.csv"), mode='w', encoding='utf-8', newline='') as file:
        escritor = csv.writer(file)
        escritor.writerow(["Autor", "Relación", "Nacionalidad"])
        escritor.writerows(rows)

def make_work_publish_date_triplets():
    path = os.path.join("centroamerica", "works_info_spanish.csv")
    rows = []
    with open(path, mode='r', encoding='utf-8') as file:
        lector = csv.reader(file)
        next(lector)
        for row in lector:
            if row[4].strip():  # Asegurarse de que la fecha de publicación no esté vacía
                rows.append([row[1], "fue_publicado_en", row[4]])

    with open(os.path.join("centroamerica", "works_publish_date_triplets.csv"), mode='w', encoding='utf-8', newline='') as file:
        escritor = csv.writer(file)
        escritor.writerow(["Obra", "Relación", "Fecha de Publicación"])
        escritor.writerows(rows)

def make_work_author_triplets():
    path = os.path.join("centroamerica", "works_info_spanish.csv")
    rows = []
    with open(path, mode='r', encoding='utf-8') as file:
        lector = csv.reader(file)
        next(lector)
        for row in lector:
            rows.append([row[1], "fue_escrito_por", row[2]])

    with open(os.path.join("centroamerica", "works_author_triplets.csv"), mode='w', encoding='utf-8', newline='') as file:
        escritor = csv.writer(file)
        escritor.writerow(["Obra", "Relación", "Autor"])
        escritor.writerows(rows)

def make_work_country_triplets():
    path = os.path.join("centroamerica", "works_info_spanish.csv")
    rows = []
    with open(path, mode='r', encoding='utf-8') as file:
        lector = csv.reader(file)
        next(lector)
        for row in lector:
            work_name = row[1]
            author_name = row[2]
            author_nationality = get_author_nationality(author_name)
            author_country = nationalities_to_countries_dictionary[author_nationality]
            rows.append([work_name, "el_autor_es_del_pais", author_country])
    
    with open(os.path.join("centroamerica", "works_country_triplets.csv"), mode='w', encoding='utf-8', newline='') as file:
        escritor = csv.writer(file)
        escritor.writerow(["Obra", "Relación", "País del Autor"])
        escritor.writerows(rows)

def get_author_nationality(author_name):
    with open(os.path.join("centroamerica", "authors_nationalities.csv"), mode='r', encoding='utf-8') as authors_file:
        authors_lector = csv.reader(authors_file)
        next(authors_lector)
        for author_row in authors_lector:
            if author_row[0] == author_name:
                return author_row[1]
    return ""

def make_work_subject_triplets():
    path = os.path.join("centroamerica", "works_info_spanish.csv")
    rows = set()
    from utils import parse_list_of_dicts
    with open(path, mode='r', encoding='utf-8') as file:
        lector = csv.reader(file)
        next(lector)
        for row in lector:
            work_name = row[1]
            raw_subjects = row[5]
            subjects_list = parse_list_of_dicts(raw_subjects)
            for subject in subjects_list:
                rows.add((work_name, "tiene_como_tema", subject))

    with open(os.path.join("centroamerica", "works_subject_triplets.csv"), mode='w', encoding='utf-8', newline='') as file:
        escritor = csv.writer(file)
        escritor.writerow(["Obra", "Relación", "Tema"])
        escritor.writerows(list(rows))

def make_work_publisher_triplets():
    path = os.path.join("centroamerica", "works_info_spanish.csv")
    rows = set()
    from utils import parse_list_of_dicts
    with open(path, mode='r', encoding='utf-8') as file:
        lector = csv.reader(file)
        next(lector)
        for row in lector:
            work_name = row[1]
            raw_editions = row[3]
            editions = parse_list_of_dicts(raw_editions)
            for edition in editions:
                publishers = edition.get("publishers", [])
                for publisher in publishers:
                    rows.add((work_name, "fue_publicado_por", publisher))

    with open(os.path.join("centroamerica", "works_publisher_triplets.csv"), mode='w', encoding='utf-8', newline='') as file:
        escritor = csv.writer(file)
        escritor.writerow(["Obra", "Relación", "Editorial"])
        escritor.writerows(list(rows))

make_work_publisher_triplets()