import requests
import json
from typing import TypedDict

SUBJECT_API_URL = "https://openlibrary.org/subjects/{subject_name}.json?limit={limit}"
USER_AGENT = "SubjectFetcher/1.0 (Python requests; contact: cibqsm@gmail.com)"
HEADERS = {"User-Agent": USER_AGENT}
TARGET_SUBJECTS = ["American Authors"]#, "Canadian Authors"]



def get_subject_data(subject_name: str, limit: int = 1) -> dict | None:
    """Fetches and returns data for a given subject from Open Library."""
    api_slug = subject_name.lower().replace(" ", "_")
    url = SUBJECT_API_URL.format(subject_name=api_slug, limit=limit)
    print(f"Fetching data for: {subject_name} from {url}")
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        if 'application/json' in response.headers.get('Content-Type', ''):
            return response.json()
        else:
            print(f"Error: Received non-JSON response for {subject_name}. Content-Type: {response.headers.get('Content-Type')}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data for {subject_name}: {e}")
        return None
    except json.JSONDecodeError as e:
         print(f"Error decoding JSON for {subject_name}: {e}")
         return None

if __name__ == "__main__":
    all_subject_data = {}
    for subject in TARGET_SUBJECTS:
        data = get_subject_data(subject)
        if data:
            all_subject_data[subject] = data
        else:
            all_subject_data[subject] = {"error": f"Failed to retrieve data for {subject}"}

    print(json.dumps(all_subject_data[subject], indent=2))

