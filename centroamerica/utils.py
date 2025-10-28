import ast
import json

def parse_list_of_dicts(s):
    """
    Convierte un string que representa una lista de diccionarios
    en una lista de diccionarios real de Python.

    Acepta tanto formato JSON ([{"a":1}]) como formato Python ([{'a':1}]).
    """
    if not isinstance(s, str):
        raise TypeError("El argumento debe ser un string")

    s = s.strip()
    if not s:
        return []

    try:
        # Primero intentamos con JSON (comillas dobles)
        return json.loads(s)
    except json.JSONDecodeError:
        try:
            # Luego intentamos con formato tipo Python (comillas simples, etc.)
            return ast.literal_eval(s)
        except (ValueError, SyntaxError) as e:
            raise ValueError(f"No se pudo convertir el string: {e}")
        

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