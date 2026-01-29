import requests

def buscar_libros(query):
    """
    Busca libros en la API de Open Library
    """
    url = f"https://openlibrary.org/search.json?q={query}&limit=10"

    respuesta = requests.get(url)

    if respuesta.status_code == 200:
        datos = respuesta.json()
        return datos.get('docs', [])
    else:
        return []

def buscar_autores(query):
    """
    Busca autores en la API de Open Library
    """
    url = f"https://openlibrary.org/search/authors.json?q={query}&limit=10"

    respuesta = requests.get(url)

    if respuesta.status_code == 200:
        datos = respuesta.json()
        return datos.get('docs', [])
    else:
        return []