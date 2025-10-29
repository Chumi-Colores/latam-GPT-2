#%%
import pandas as pd

seed = 28
samples_per_question = 100

data = pd.read_csv('../data/knowledge_graph.csv')

#%% 1. Type 1

author_rel = data[data.relacion=='es_autor_de_la_obra']
author_samples = author_rel.sample(samples_per_question, random_state=seed, replace=False)

author_samples['Pregunta'] = '¿Quién escribio el libro "' + author_samples.objeto + '"?'
author_samples['Question'] = 'Who wrote the book "' + author_samples.objeto + '"?'
author_samples['Respuesta'] = author_samples['sujeto']
author_samples['Answer'] = author_samples['sujeto']
author_samples['Type'] = 'P1'
author_samples['Tipo'] = 'P1'
df_p1_esp = author_samples[['Tipo', 'Pregunta', 'Respuesta']].copy()
df_p1_eng = author_samples[['Type', 'Question', 'Answer']].copy()

del author_samples

# %% 2. Type 2
country_rel = data[data.relacion=='es_de']

author_book_country = pd.merge(author_rel, country_rel, on='sujeto')[['sujeto', 'objeto_x', 'objeto_y']]
author_book_country.rename(columns={'objeto_x': 'book', 'objeto_y': 'country'}, inplace=True)
author_book_country = author_book_country.sample(samples_per_question, random_state=seed, replace=False)

author_book_country['Pregunta'] = '¿De qué país es el autor de "' + author_book_country.book + '"?'
author_book_country['Question'] = 'What country is the author of "' + author_book_country.book + '" from?'
author_book_country['Respuesta'] = author_book_country['country']
author_book_country['Answer'] = author_book_country['country']
author_book_country['Type'] = 'P2'
author_book_country['Tipo'] = 'P2'
df_p2_esp = author_book_country[['Tipo', 'Pregunta', 'Respuesta']].copy()
df_p2_eng = author_book_country[['Type', 'Question', 'Answer']].copy()

del author_book_country
# %% 3. Type 3

year_rel = data[data.relacion=='fue_publicado_en']
year_rel = year_rel.drop_duplicates(subset=['sujeto', 'objeto'], keep='first')

year_samples = year_rel.sample(samples_per_question, random_state=seed, replace=False)

year_samples['Pregunta'] = '¿En que año se publicó "' + year_samples.sujeto + '"?'
year_samples['Question'] = 'In what year was "' + year_samples.sujeto + '" published?'
year_samples['Respuesta'] = year_samples['objeto']
year_samples['Answer'] = year_samples['objeto']
year_samples['Type'] = 'P3'
year_samples['Tipo'] = 'P3'
df_p3_esp = year_samples[['Tipo', 'Pregunta', 'Respuesta']].copy()
df_p3_eng = year_samples[['Type', 'Question', 'Answer']].copy()

del year_samples
# %% 4. Type 4

category_rel = data[data.relacion == 'tiene_categoría']
category_rel = category_rel.groupby(['sujeto', 'relacion']).head(10)
category_rel = category_rel.groupby(['sujeto', 'relacion'])['objeto'].agg(list).reset_index()

category_sample = category_rel.sample(samples_per_question, random_state=seed, replace=False)

category_sample['Pregunta'] = '¿Cual es la categoria o genero del libro "' + category_sample.sujeto + '"?'
category_sample['Question'] = 'What is the category or genre of the book "' + category_sample.sujeto + '"?'
category_sample['Respuesta'] = category_sample['objeto']
category_sample['Answer'] = category_sample['objeto']
category_sample['Type'] = 'P4'
category_sample['Tipo'] = 'P4'
df_p4_esp = category_sample[['Tipo', 'Pregunta', 'Respuesta']].copy()
df_p4_eng = category_sample[['Type', 'Question', 'Answer']].copy()

del category_sample
# %% 5. Type 5


edition_rel = data[data.relacion=='tiene_edicion']
editorial_rel = data[data.relacion=='fue_publicado_por']
editorial_rel.columns = editorial_rel.columns[::-1]


book_editorial = pd.merge(edition_rel, editorial_rel, on='objeto')[['sujeto_x', 'sujeto_y']]
book_editorial.rename(columns={'sujeto_x': 'book', 'sujeto_y': 'editorial'}, inplace=True)

book_editorial = book_editorial.groupby(['book'], as_index=False)['editorial'].agg(lambda x: list(set(x)))

book_editorial = book_editorial.sample(samples_per_question, random_state=seed, replace=False)

book_editorial['Pregunta'] = '¿Qué editoriales han publicado el libro "' + book_editorial.book + '"?'
book_editorial['Question'] = 'Which publishers have published the book "' + book_editorial.book + '"?'
book_editorial['Respuesta'] = book_editorial['editorial']
book_editorial['Answer'] = book_editorial['editorial']
book_editorial['Type'] = 'P5'
book_editorial['Tipo'] = 'P5'
df_p5_esp = book_editorial[['Tipo', 'Pregunta', 'Respuesta']].copy()
df_p5_eng = book_editorial[['Type', 'Question', 'Answer']].copy()

del book_editorial


#%% Concat Questions 

questions_esp = pd.concat([df_p1_esp, df_p2_esp, df_p3_esp, df_p4_esp, df_p5_esp], axis=0).reset_index(drop=True)
questions_eng = pd.concat([df_p1_eng, df_p2_eng, df_p3_eng, df_p4_eng, df_p5_eng], axis=0).reset_index(drop=True)

questions_esp.to_csv('../data/questions_esp.csv', index=False)
questions_eng.to_csv('../data/questions_eng.csv', index=False)
