import json
import requests
import urllib.parse

from glom import glom
from termcolor import colored
from tabulate import tabulate
from requests.models import PreparedRequest


COOKIE = '_session_id=c3V1Vi9ldU5aZ3YvZGRxbWcvL0w2eFI1REh0eHJPalpWTldoUnZGT25ldUd1UjZwN3VteERIRmJBOWlqdWJJQndkWVQ5RllCZjh4cUIrL2NDa1lnV0ZJZ054VDVDK1RjV0c0blo5MUEzTUhQSHlLL3BXQlgzRXFMcE5zL1BWNGEyZUlTR3Z0K3c2cXhpQW0yd2RrVEJEYWV0U0pidFhsMHhoMVdMaXpiYS9HRTdKQ053eWV4NHFxQ2Q1QUdXcDR6TGxUdTVPd29lVCtKaXg1dzRPbFJ3UGlWRDZUT0NxZXl5MTVhS1JPWWhGZz0tLW1Fb3c4cVhORHBpamhKMGJhcGRFbWc9PQ%3D%3D--b701461c4292af6bee106d87923fae4a711c4247; _seedlang_session=UlY1L2MwbXNKL1J6VmRmTW9wLzFNTTB6NnFsOUlvai9RWVRQUWVwbmVnek4wcFczbDh2VFd3d1ZUOTJiNElxMHkzVkt6dVhha252WjY5VXRWU3BRYzdsN2IrK2t2TnQ1dFpZRER6K0c5Z2JUOTdQbTE0NDdVYWRFdTduYzFSYXNiVVdIZ3pDY3FvTzdFYTRrbUNmK0lSWkJPNEtKbkNkSmhKSTJOc1YrMy9JQnVhYm1jVG5PRjJFVmRkRTl0V2lOSk1zZlZaQ0VEWHlpRVRLTHZmbjFWL2tKWUlyUndIMDhucFVkTEttT2wrTT0tLWI0VTVwOFcrVmZwTGp4ZUoyTFNpZ2c9PQ%3D%3D--390ca2cc6e2ba607b5ca472b3804ba1446ed3d66'
USER_ID = '13e307d4-4547-45f8-a0de-77c72edabd29'

COOKIE_MAP = {}

def init_cookie_map():
  for cookie_token in COOKIE.split(";"):
    cookie_key, cookie_value = cookie_token.split("=")
    COOKIE_MAP[cookie_key] = cookie_value

def get(api_url):
  print(colored("[GET]", 'white', 'on_green', attrs=['bold']) + " " + api_url + " ...")
  return requests.get(api_url, cookies=COOKIE_MAP).json()

def post(api_url, payload):
  print(colored("[POST]", 'white', 'on_red', attrs=['bold']) + " " + api_url + " ...")
  return requests.get(api_url, cookies=COOKIE_MAP, json=payload).json()

def print_json(data):
  print(json.dumps(data, indent=2))

# ----- API Callers -----

def get_words_list(page: int = 1):
  url = "https://seedlang.com/api/words"
  params = {
    "sort": "frequency_ranking",
    "limit": 20,
    "vocab_list": True,
    "filters[root]": True,
    "filters[video_clip_id]": True,
    "filters[language_id]": "DE",
    "page": page,
  }

  req = PreparedRequest()
  req.prepare_url(url, params)
  return get(req.url)

def search_words_list(word_query: str):
  url = "https://seedlang.com/api/words"
  params = {
    "sort": "frequency_ranking",
    "limit": 20,
    "vocab_list": True,
    "filters[root]": True,
    "filters[video_clip_id]": True,
    "filters[language_id]": "DE",
    "filters[target_text]": f'~{word_query}~',
    # "filters[level_id]": "8f53a51c-a6db-42ef-b865-b766ddc8ac64",
  }

  req = PreparedRequest()
  req.prepare_url(url, params)
  return get(req.url)

def get_word_details(id: str):
  url = "https://seedlang.com/api/words/" + str(id)
  print("[GET]" + url + " ...")

  return get(url)

def get_word_example_sentences(word_id: str):
  url = "https://seedlang.com/api/sentences"
  params = {
    "word_id": word_id,
    "sort": 20,
    "vocab_list": "level_abbreviation,%20target_text",
    "vocab_trainer": True
  }

  req = PreparedRequest()
  req.prepare_url(url, params)
  return get(req.url)

def add_word_to_reviews(word_id: str):
  url = "https://seedlang.com/api/sentences"
  payload = {
    "interface_source": "vocab-word",
    "card_type_slug": "vocab_word_translate",
    "card_type_id": None,
    "deck_id": "42d997a9-1ac7-4086-9754-deab6568719d",
    "user_id": USER_ID,
    "word_id": word_id,
    "sentence_id": False,
    "language_id": "DE"
  }

  return post(url, payload)

# ----- Logic handlers -----

def format_word(word_data):
  word_text = word_data['target_text']

  if word_data['word_type']['abbreviation'] != 'noun':
    return colored(word_text, 'white', attrs=["bold"])

  GENDER_MAPPINGS = { "feminine": "e", "masculine": "r", "neuter": "s"}

  gender = GENDER_MAPPINGS[ word_data['gender'] ] + ","
  plural_word_text = word_data["plural_nouns"][0]["target_text"]
  plural_suffix = plural_word_text.replace(word_text, '')

  return colored(gender, 'cyan') \
    + colored(word_text, 'light_green', attrs=['bold']) \
    + colored("-" + plural_suffix, 'magenta') if not word_data['no_plural'] else ''

def format_word_type(word_data):
  abbrev_text = word_data["word_type"]["abbreviation"]
  wordtype_mappings = {
    "noun": colored("N", 'light_green'),
    "adj": colored("A", "yellow"),
    "adv": colored("Adv", "yellow"),
    "vrb": colored("V", 'red'),
  }
  return wordtype_mappings.get(abbrev_text, abbrev_text)

def format_translations(word_data):
  translations = word_data["translation_sources"]
  render_text = "; ".join([ translation["source"]["text"] for translation in translations ])
  return render_text[:60] + (render_text[60:] and '...')

def print_list_word(page: int = 1, hide_learned: bool = False):
  words = get_words_list(page)["data"]

  display_rows = []
  headers = list(map(
    lambda h: colored(h, 'white', attrs=['bold']),
    ['TYPE', 'WORD', 'FREQ', 'LEVEL', 'LEARN_STATUS', 'TRANSLATION', 'WORD_ID']
  ))

  for word in words:
    if hide_learned and word['learned']: continue

    display_row = [
      format_word_type(word),
      format_word(word),
      word["frequency_ranking"],
      word["level"]["abbreviation"],
      '✅' if word["learned"] else ('⌛' if word["reviewing"] else '  '),
      format_translations(word),
      word["id"],
    ]

    if word["learned"]:
      display_row = list(map(
        lambda cv: colored(cv, attrs=['dark']),
        display_row
      ))

    display_rows += [ display_row ]

  print("\n" + colored(f"LIST WORD - PAGE: {page}", 'white', attrs=['bold']))
  print(tabulate(display_rows,headers))

# -----

def main():
  print_list_word(1, hide_learned=False)

if __name__ == '__main__':
  init_cookie_map()
  main()