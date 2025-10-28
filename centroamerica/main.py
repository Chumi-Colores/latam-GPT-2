import csv
from get_authors_and_their_isbns import get_works_info_from_author, get_authors_from_country, countries_to_nationalities_dictionary, countries_that_work
from utils import parse_list_of_dicts

def get_number_of_written_files():
    import os
    files = os.listdir("centroamerica")
    count = 0
    for file in files:
        if file.startswith("works_info_") and file.endswith(".csv"):
            count += 1
    return count

def get_number_of_lines_in_file(file_path):
    #first we check if file exists
    import os
    if not os.path.exists(file_path):
        return 0
    with open(file_path, mode='r', encoding='utf-8') as file:
        return sum(1 for _ in file)

def get_and_save_authors_and_nationalities():
    authors_nationalities_path = "centroamerica/authors_nationalities.csv"
    authors_nationalities_file = open(authors_nationalities_path, mode='w', encoding='utf-8', newline='')
    csv_writer = csv.writer(authors_nationalities_file)
    csv_writer.writerow(["Author", "Nationality"])

    for country in countries_that_work:
        authors = get_authors_from_country(countries_to_nationalities_dictionary[country])
        for author_key, author_data in authors.items():
            csv_writer.writerow([author_data["name"], author_data["nationality"]])

    authors_nationalities_file.close()

def get_and_save_works_info_from_author(authors):
    authors_written = 0
    lines_written = 0
    max_lines_per_file = 2000
    files_written = get_number_of_written_files()
    works_info_path = f"centroamerica/works_info_{files_written}.csv"
    lines_written = get_number_of_lines_in_file(works_info_path) if files_written > 0 else 0
    works_info_file = open(works_info_path, mode='a', encoding='utf-8', newline='')
    csv_writer = csv.writer(works_info_file)
    # add header if empty file
    if works_info_file.tell() == 0:
        csv_writer.writerow(["Work ID", "Title", "Author", "Editions", "Publish_date", "Subjects"])

    while authors_written < len(authors):
        if lines_written >= max_lines_per_file:
            works_info_file.close()
            files_written += 1
            works_info_path = f"centroamerica/works_info_{files_written}.csv"
            works_info_file = open(works_info_path, mode='a', encoding='utf-8', newline='')
            csv_writer = csv.writer(works_info_file)
            if works_info_file.tell() == 0:
                csv_writer.writerow(["Work ID", "Title", "Author", "Editions", "Publish_date", "Subjects"])
            lines_written = 0
        
        if check_if_author_done(authors[authors_written]["name"]):
            authors_written += 1
            continue

        author_name = authors[authors_written]["name"]
        works_info = get_works_info_from_author(author_name)

        for work_id, work in works_info.items():
            csv_writer.writerow([work_id, work["title"], author_name, work["editions"], work["publish_date"], work["subjects"]])
            lines_written += 1
        authors_written += 1
        mark_author_as_done(author_name)
        print(f"Processed authors: {authors_written}/{len(authors)}")

    works_info_file.close()

def mark_author_as_done(author_name):
    done_authors_path = "centroamerica/done_authors.txt"
    with open(done_authors_path, mode='a', encoding='utf-8') as done_authors_file:
        done_authors_file.write(f"{author_name}\n")

def check_if_author_done(author_name) -> bool:
    done_authors_path = "centroamerica/done_authors.txt"
    try:
        with open(done_authors_path, mode='r', encoding='utf-8') as done_authors_file:
            done_authors = done_authors_file.read().splitlines()
            return author_name in done_authors
    except FileNotFoundError:
        return False

def remove_duplicates_from_works_info():
    works_info_path = "centroamerica/works_info.csv"
    unique_works = {}
    with open(works_info_path, mode='r', encoding='utf-8') as file:
        lector = csv.reader(file)
        next(lector)  # skip header
        for row in lector:
            work_id = row[0]
            if work_id not in unique_works:
                unique_works[work_id] = row

    works_info_no_duplicates_path = "centroamerica/works_info_no_duplicates.csv"
    with open(works_info_no_duplicates_path, mode='w', encoding='utf-8', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Work ID", "Title", "Author", "Editions", "Publish_date", "Subjects"])
        for work in unique_works.values():
            writer.writerow(work)

def remove_works_not_in_spanish():
    works_info_path = "centroamerica/works_info_no_duplicates.csv"
    works_in_spanish = []
    with open(works_info_path, mode='r', encoding='utf-8') as file:
        lector = csv.reader(file)
        next(lector)  # skip header
        for row in lector:
            raw_editions = row[3]
            editions = parse_list_of_dicts(raw_editions)
            languages = []
            for edition in editions:
                languages += edition.get("languages", [])
            if "Spanish" in languages:
                works_in_spanish.append(row)

    works_info_spanish_path = "centroamerica/works_info_spanish.csv"
    with open(works_info_spanish_path, mode='w', encoding='utf-8', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Work ID", "Title", "Author", "Editions", "Publish_date", "Subjects"])
        for work in works_in_spanish:
            writer.writerow(work)

remove_works_not_in_spanish()