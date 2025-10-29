import google.genai as genai
import dotenv
import os


#Obtener API KEY en https://aistudio.google.com/welcome
#pip install google-generativeai
# Crear .env con API_KEY=


dotenv.load_dotenv()

API_KEY = os.getenv("API_KEY")

client = genai.Client(api_key=API_KEY) 



primera_pregunta = "A qué categoría pertenece la obra Miguel Vicente Pata Caliente/Hot-Footed Miguel Vicente?"
segunda_pregunta = "Estas son las categorias a las que pertenece la obra: Infantil / Juvenil, Educación. ¿Respondiste bien? Responde con sí o no."
        

            
first_prompt = primera_pregunta + ". Entrega solo una categoria"

response = client.models.generate_content(
    model="gemini-2.5-flash-lite",
    contents=first_prompt
)

model_answer = response.text

prompt_followup = f"Tu respuesta a la pregunta {first_prompt} fue {model_answer}. {segunda_pregunta}"

response = client.models.generate_content(
    model="gemini-2.5-flash-lite",
    contents=prompt_followup
)

print(response.text)
