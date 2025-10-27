import wikipediaapi
import csv

def obtain_authors(page, nationality):
    wiki_es = wikipediaapi.Wikipedia(
        user_agent='desafio-ia (ejemplo@mail.com)',
        language='es'
    )

    cat = wiki_es.page(page)

    output_file = f"escritores_{nationality}.csv"

    
    with open(output_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["author"])  

        for title in cat.categorymembers.keys():
            writer.writerow([title])



if __name__ == "__main__":
    #modificar por el titulo de la pagina de wikipedia con la lista y la nacionalidad
    obtain_authors("Categoría:Escritoras de Paraguay", "paraguayos")