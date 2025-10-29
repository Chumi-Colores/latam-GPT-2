import google.generativeai as genai
import dotenv
import os


#Obtener API KEY en https://aistudio.google.com/welcome
#pip install google-generativeai
# Crear .env con API_KEY=


dotenv.load_dotenv()

API_KEY = os.getenv("API_KEY")

client = genai.Client(api_key=API_KEY) 

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Write a quick summary about the Gemini API."
)
print(response.text)