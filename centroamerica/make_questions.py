import random
import os
import csv
import json

def make_question_about_author_name_from_work_title() -> tuple[str, list[str]]:
    with open(os.path.join("centroamerica", "triplets", "works_author_triplets.csv"), mode='r', encoding='utf-8') as file:
        lector = csv.reader(file)
        next(lector)
        rows = list(lector)
    chosen_work_for_question = random.sample(rows, 1)[0]
    chosen_work_title = chosen_work_for_question[0]
    chosen_author_name = chosen_work_for_question[2]
    author_options = get_n_random_authors(6)
    author_options = [author[0] for author in author_options]
    if chosen_author_name not in author_options:
        author_options.pop(0)
        author_options.append(chosen_author_name)
    random.shuffle(author_options)
    question = f"Who is the author of the work titled: '{chosen_work_title}'?\na) {author_options[0]}\nb) {author_options[1]}\nc) {author_options[2]}\nd) {author_options[3]}\ne) {author_options[4]}\nf) {author_options[5]}"
    return question, [chosen_author_name]

def make_question_about_author_country_from_work_title() -> tuple[str, list[str]]:
    with open(os.path.join("centroamerica", "triplets", "works_country_triplets.csv"), mode='r', encoding='utf-8') as file:
        lector = csv.reader(file)
        next(lector)
        rows = list(lector)
    chosen_work_for_question = random.sample(rows, 1)[0]
    chosen_work_title = chosen_work_for_question[0]
    chosen_work_country = chosen_work_for_question[2]
    question = f"What country is the author of the work titled: '{chosen_work_title}' from?"
    return question, [chosen_work_country]

def make_question_about_publish_date_from_work_title() -> tuple[str, list[str]]:
    with open(os.path.join("centroamerica", "triplets", "works_publish_date_triplets.csv"), mode='r', encoding='utf-8') as file:
        lector = csv.reader(file)
        next(lector)
        rows = list(lector)
    chosen_work_for_question = random.sample(rows, 1)[0]
    chosen_work_title = chosen_work_for_question[0]
    chosen_publish_date = chosen_work_for_question[2]
    question = f"When was the work titled: '{chosen_work_title}' published?"
    return question, [chosen_publish_date.split("-")[0]]  # Solo el año

def make_question_about_subjects_from_work_title() -> tuple[str, list[str]]:
    with open(os.path.join("centroamerica", "triplets", "works_subject_triplets.csv"), mode='r', encoding='utf-8') as file:
        lector = csv.reader(file)
        next(lector)
        rows = list(lector)
    chosen_work = random.sample(rows, 1)[0]
    chosen_work_title = chosen_work[0]
    subjects_list = [row[2] for row in rows if row[0] == chosen_work[0]]
    question = f"What is the main subject or genre from the work titled: '{chosen_work_title}'?"
    return question, subjects_list

def make_question_about_publisher_from_work_title() -> tuple[str, list[str]]:
    with open(os.path.join("centroamerica", "triplets", "works_publisher_triplets.csv"), mode='r', encoding='utf-8') as file:
        lector = csv.reader(file)
        next(lector)
        rows = list(lector)
    chosen_work = random.sample(rows, 1)[0]
    chosen_work_title = chosen_work[0]
    chosen_work_publishers = [row[2] for row in rows if row[0] == chosen_work[0]]
    question = f"What publisher has published the work titled: '{chosen_work_title}'?"
    return question, chosen_work_publishers

def get_n_random_authors(n):
    path = os.path.join("centroamerica", "authors_nationalities.csv")
    authors = []
    with open(path, mode='r', encoding='utf-8') as file:
        lector = csv.reader(file)
        next(lector)
        for row in lector:
            authors.append((row[0], row[1]))
    return random.sample(authors, n)

functions_names = {
    "author_name_from_work_title": make_question_about_author_name_from_work_title,
    "author_country_from_work_title": make_question_about_author_country_from_work_title,
    "publish_date_from_work_title": make_question_about_publish_date_from_work_title,
    "subjects_from_work_title": make_question_about_subjects_from_work_title,
    "publisher_from_work_title": make_question_about_publisher_from_work_title
}

if __name__ == "__main__":
    os.makedirs("centroamerica/test_questions", exist_ok=True)
    for key, func in functions_names.items():
        # create and write json file
        questions = []
        for _ in range(100):
            question, answers = func()
            questions.append({
                "question": question,
                "answers": answers
            })
        with open(os.path.join("centroamerica", "test_questions", f"{key}_questions.json"), mode='w', encoding='utf-8') as file:
            json.dump(questions, file, ensure_ascii=False, indent=4)
        