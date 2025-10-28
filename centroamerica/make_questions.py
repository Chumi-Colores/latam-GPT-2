import random
import os
import csv
from utils import parse_list_of_dicts

nationalities_to_countries_dictionary = {
    "aruban": "Aruba",
    "bahamian": "Bahamas",
    "cuban": "Cuba",
    "jamaican": "Jamaica",
    "barbadian": "Barbados",
    "bermudian": "Bermuda",
    "bonairean": "Bonaire",
    "caymanian": "Cayman Islands",
    "curacaoan": "Curacao",
    "dominican": "Dominican Republic",
    "grenadian": "Grenada",
    "guadeloupean": "Guadeloupe",
    "haitian": "Haiti",
    "martiniquais": "Martinique",
    "montserratian": "Montserrat",
    "puerto_rican": "Puerto Rico",
    "trinidadian_and_tobagonian": "Trinidad and Tobago",
    "mexican": "Mexico",
    "belizean": "Belize",
    "guatemalan": "Guatemala",
    "salvadoran": "El Salvador",
    "honduran": "Honduras",
    "nicaraguan": "Nicaragua",
    "costarican": "Costa Rica",
    "panamanian": "Panama"
}

def make_question_about_author_name_from_work_title() -> tuple[str, list[str]]:
    works = get_n_random_works(1)
    work_title = works[0][1]
    work_author = works[0][2]
    options = get_n_random_authors(6)
    options = [author[0] for author in options]
    if work_author not in options:
        options.pop(0)
        options.append(work_author)
    random.shuffle(options)
    question = f"Who is the author of the work titled: '{work_title}'?\na) {options[0]}\nb) {options[1]}\nc) {options[2]}\nd) {options[3]}\ne) {options[4]}\nf) {options[5]}"
    return question, [work_author]

def make_question_about_author_country_from_work_title() -> tuple[str, list[str]]:
    works = get_n_random_works(1)
    work_title = works[0][1]
    work_author = works[0][2]
    question = f"What country is the author of the work titled: '{work_title}' from?"
    nationality = get_nationality_from_author(work_author)
    answer = nationalities_to_countries_dictionary[nationality]
    return question, [answer]

def make_question_about_publish_date_from_work_title() -> tuple[str, list[str]]:
    works = get_n_random_works(1)
    work_title = works[0][1]
    publish_date = works[0][4]
    question = f"When was the work titled: '{work_title}' published?"
    return question, [publish_date]

def make_question_about_subjects_from_work_title() -> tuple[str, list[str]]:
    while True:
        works = get_n_random_works(1)
        work_title = works[0][1]
        raw_subjects = works[0][5]
        subjects_list = parse_list_of_dicts(raw_subjects)
        if len(subjects_list) != 0:
            question = f"What is the main genre or subject from the work titled: '{work_title}'?"
            return question, subjects_list

def make_question_about_publisher_from_work_title() -> tuple[str, list[str]]:
    works = get_n_random_works(1)
    work_title = works[0][1]
    raw_editions = works[0][3]
    editions = parse_list_of_dicts(raw_editions)
    publishers = []
    for edition in editions:
        publishers += edition.get("publishers", [])
    if not publishers:
        publishers = ["Unknown"]
    question = f"What publisher has published the work titled: '{work_title}'?"
    return question, publishers

def get_n_random_works(n):
    path = os.path.join("centroamerica", "works_info_spanish.csv")
    works = []
    with open(path, mode='r', encoding='utf-8') as file:
        lector = csv.reader(file)
        next(lector)
        for row in lector:
            works.append(row)
    return random.sample(works, n)

def get_n_random_authors(n):
    path = os.path.join("centroamerica", "authors_nationalities.csv")
    authors = []
    with open(path, mode='r', encoding='utf-8') as file:
        lector = csv.reader(file)
        next(lector)
        for row in lector:
            authors.append((row[0], row[1]))
    return random.sample(authors, n)

def get_nationality_from_author(author_name):
    path = os.path.join("centroamerica", "authors_nationalities.csv")
    with open(path, mode='r', encoding='utf-8') as file:
        lector = csv.reader(file)
        next(lector)
        for row in lector:
            if row[0] == author_name:
                return row[1]
    raise ValueError(f"Author '{author_name}' not found in the database.")

if __name__ == "__main__":
    question, answer = make_question_about_publisher_from_work_title()
    print(question)
    print(f"Answer: {answer}")