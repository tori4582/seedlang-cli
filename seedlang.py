import json
import requests
import typer
import urllib.parse
import webbrowser

from glom import glom
from termcolor import colored
from tabulate import tabulate
from requests.models import PreparedRequest

from rich import print as rich_print
from rich.console import Console
from rich.markdown import Markdown
from rich.columns import Columns
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, TextColumn
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed

COOKIE = ""
USER_ID = "13e307d4-4547-45f8-a0de-77c72edabd29"

COOKIE_MAP = {}

typer_app = typer.Typer()
rich_console = Console()


def init_cookie_map():
    for cookie_token in COOKIE.split(";"):
        cookie_key, cookie_value = cookie_token.split("=")
        COOKIE_MAP[cookie_key] = cookie_value


def get(api_url):
    print(
        colored("[GET]", "white", "on_green", attrs=["bold"]) + " " + api_url + " ..."
    )
    return requests.get(api_url, cookies=COOKIE_MAP, timeout=15).json()


def post(api_url, payload):
    print(
        colored("[POST]", "white", "on_yellow", attrs=["bold"])
        + " "
        + api_url
        + " ... ",
        end="",
    )
    response = requests.get(api_url, cookies=COOKIE_MAP, json=payload, timeout=15)

    print(response.status_code)

    if response.status_code in range(200, 300):
        return response.json()

    raise ValueError(str(response.status_code) + " " + response.reason)


def put(api_url, payload):
    print(
        colored("[PUT]", "blue", "on_blue", attrs=["bold"]) + " " + api_url + " ... ",
        end="",
    )
    response = requests.put(api_url, cookies=COOKIE_MAP, json=payload, timeout=15)
    print(response.status_code)

    if response.status_code in range(200, 300):
        return response.json()

    raise ValueError(str(response.status_code) + " " + response.reason)


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


def search_word(word_query: str, limit: int, page: int):
    url = "https://seedlang.com/api/words"
    params = {
        "sort": "frequency_ranking",
        "limit": limit,
        "page": page,
        "vocab_list": True,
        "filters[root]": True,
        "filters[video_clip_id]": True,
        "filters[language_id]": "DE",
        "filters[target_text]": f"~{word_query}~",
        # "filters[level_id]": "8f53a51c-a6db-42ef-b865-b766ddc8ac64",
    }

    req = PreparedRequest()
    req.prepare_url(url, params)
    return get(req.url)


def get_word_details(id: str):
    url = "https://seedlang.com/api/words/" + str(id)
    return get(url)


def get_word_example_sentences(word_id: str):
    url = "https://seedlang.com/api/sentences"
    params = {
        "word_id": word_id,
        "sort": 20,
        "vocab_list": "level_abbreviation,%20target_text",
        "vocab_trainer": True,
    }

    req = PreparedRequest()
    req.prepare_url(url, params)
    return get(req.url)


def add_word_to_reviews(word_id: str):
    url = "https://seedlang.com/api/cards"
    payload = {
        "data": {
            "interface_source": "vocab-word",
            "card_type_slug": "vocab_word_translate",
            "card_type_id": None,
            "deck_id": "42d997a9-1ac7-4086-9754-deab6568719d",
            "user_id": USER_ID,
            "word_id": word_id,
            "sentence_id": False,
            "language_id": "DE",
        }
    }

    return post(url, payload)


# ----- Logic handlers -----


def get_word_type_color(word_type_abbrev):
    return {"noun": "light_green", "adj": "yellow", "adv": "yellow", "vrb": "red"}.get(
        word_type_abbrev, ""
    )


def format_word(word_data):
    word_text = word_data["target_text"]

    if word_data["word_type"]["abbreviation"] != "noun":
        return colored(word_text, "white", attrs=["bold"])

    GENDER_MAPPINGS = {"feminine": "e", "masculine": "r", "neuter": "s"}

    gender = GENDER_MAPPINGS[word_data["gender"]] + ","
    plural_word_text = (
        word_data["plural_nouns"][0]["target_text"]
        if (not word_data["no_plural"]) and word_data["plural_nouns"]
        else ""
    )
    plural_suffix = plural_word_text.replace(word_text, "")

    return (
        colored(gender, "cyan")
        + colored(word_text, "light_green", attrs=["bold"])
        + (
            colored("-" + plural_suffix, "magenta")
            if not word_data["no_plural"]
            else ""
        )
    )


def format_word_type(word_data):
    abbrev_text = word_data["word_type"]["abbreviation"]
    word_type_color = get_word_type_color(abbrev_text)
    wordtype_mappings = {"noun": "N", "adj": "A", "adv": "Adv", "vrb": "V"}
    display_text = colored(
        wordtype_mappings.get(abbrev_text, abbrev_text), word_type_color
    )

    return display_text


def format_translations(word_data):
    translations = word_data["translation_sources"]
    render_text = "; ".join(
        [translation["source"]["text"] for translation in translations]
    )
    return render_text[:60] + (render_text[60:] and "...")


@typer_app.command("page")
def print_list_word(page: int, hide_learned: bool = False):
    words = get_words_list(page)["data"]

    display_rows = []
    headers = list(
        map(
            lambda h: colored(h, "white", attrs=["bold"]),
            ["TYPE", "WORD", "FREQ", "LEVEL", "LEARN_STATUS", "TRANSLATION", "WORD_ID"],
        )
    )

    for word in words:
        if hide_learned and word["learned"]:
            continue

        display_row = [
            format_word_type(word),
            format_word(word),
            word["frequency_ranking"],
            word["level"]["abbreviation"],
            "✅" if word["learned"] else ("⌛" if word["reviewing"] else "  "),
            format_translations(word),
            word["id"],
        ]

        if word["learned"]:
            display_row = list(map(lambda cv: colored(cv, attrs=["dark"]), display_row))

        display_rows += [display_row]

    print("\n" + colored(f"LIST WORD - PAGE: {page}", "white", attrs=["bold"]))
    print(tabulate(display_rows, headers))


@typer_app.command("search")
def print_searched_word(
    word_query,
    hide_learned: bool = False,
    page: int = 1,
    page_size: int = 20,
    first: bool = False,
):
    words = search_word(word_query, page_size, page)["data"]

    display_rows = []
    headers = list(
        map(
            lambda h: colored(h, "white", attrs=["bold"]),
            ["TYPE", "WORD", "FREQ", "LEVEL", "LEARN_STATUS", "TRANSLATION", "WORD_ID"],
        )
    )

    for word in words:
        if hide_learned and word["learned"]:
            continue

        display_row = [
            format_word_type(word),
            format_word(word),
            word["frequency_ranking"],
            word["level"]["abbreviation"],
            "✅" if word["learned"] else ("⌛" if word["reviewing"] else "  "),
            format_translations(word),
            word["id"],
        ]

        if word["learned"]:
            display_row = list(map(lambda cv: colored(cv, attrs=["dark"]), display_row))

        display_rows += [display_row]

    print(
        "\n"
        + colored(f"LIST WORD - WORD QUERY: '~{word_query}~'", "white", attrs=["bold"])
    )
    print(tabulate(display_rows, headers))

    if first and words:
        print("Enabled 'First word matched' mode. Gathering definitions ...")
        print_word_definition(words[0]["id"])


def gather_parallel_word_details(word_id):
    word_resources = {}
    word = get_word_details(word_id)
    word_resources["word"] = word

    parallel_results = []

    def _get(key, url):
        return {"url": url, "response": get(url), "key": key}

    # def get_word_example_sentences(word_id: str):
    #   url = "https://seedlang.com/api/sentences"
    #   params = {
    #     "word_id": word_id,
    #     "sort": 20,
    #     "vocab_list": "level_abbreviation,%20target_text",
    #     "vocab_trainer": True
    #   }

    params = [
        ["ipa", "https://www.dwds.de/api/ipa/?q=" + word["target_text"]],
        [
            "faztaa",
            ("https://api.faztaa.com/api/search/en/devi/" + word["target_text"]),
        ],
        [
            "examples",
            (
                f"https://seedlang.com/api/sentences?word_id={word_id}&sort=20&vocab_list=level_abbreviation,%20target_text&vocab_trainer=true"
            ),
        ],
        [
            "is_added",
            (
                f"https://seedlang.com/api/cards?filters[user_id]={USER_ID}&filters[word_id]={word_id}&filters[sentence_id]=false&limit=20&page=1&my_reviews=true"
            ),
        ],
    ]

    if word["word_type"]["abbreviation"] == "vrb":
        params += [
            [
                "verb_conjugations",
                (
                    f"https://seedlang.com/api/words/{word_id}/conjugated_verb_strings?limit=20&page=1"
                ),
            ]
        ]

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = []
        for param in params:
            futures += [executor.submit(_get, param[0], param[1])]
        # parallel_results = list(executor.map(_get, **params))
        for future in as_completed(futures):
            fr = future.result()
            word_resources[fr["key"]] = fr["response"]

    # post-gather processing
    word_resources["faztaa"] = word_resources["faztaa"]["result"][0]

    if type(word_resources["is_added"]) == "list":
        word_resources["is_added"] = bool(len(word_resources["is_added"]))
    elif type(word_resources["is_added"]) == "dict":
        word_resources["is_added"] = bool(len(word_resources["is_added"]["data"]))

    return word_resources


@typer_app.command("word")
def print_word_definition(word_id):
    word_resources = gather_parallel_word_details(word_id)

    word = word_resources["word"]
    word_examples = word_resources["examples"]
    faztaa_first_result = word_resources["faztaa"]
    is_added_to_deck = word_resources["is_added"]

    ipa_entries = word_resources["ipa"]
    ipas_display_text = " ; ".join([entry["ipa"] for entry in ipa_entries])

    formatted_word = format_word(word)

    # print word title -----------------------------------------------------------
    print()
    rich_console.print(
        Panel(
            # word
            f"\n{ formatted_word }\n",
            title=format_word_type(word)
            + " - "
            + word["word_type"]["name"],  # word type
            subtitle=colored(ipas_display_text, attrs=["dark"]),  # IPA
            title_align="left",
            subtitle_align="left",
            border_style=get_word_type_color(word["word_type"]["abbreviation"]),
        )
    )

    # print word's attributes on seedlang ----------------------------------------
    table = Table()
    table.add_column("Level")
    table.add_column("Learn Status")
    table.add_column("In deck ?")

    table.add_row(
        word["level"]["abbreviation"],
        "learned" if word["learned"] else ("reviewing" if word["reviewing"] else "  "),
        "ADDED" if is_added_to_deck else "",
    )

    rich_console.print(table)
    rich_console.print(":play_button:", end=" ")
    print(
        colored("Listen the word in contexts: ", "white", attrs=["bold"])
        + f"https://youglish.com/pronounce/{word['target_text']}/german"
    )

    # print word's translation ---------------------------------------------------
    print("\n" + colored("TRANSLATIONS - seedlang's source: ", "white", attrs=["bold"]))
    translations = word["translation_sources"]
    render_lines = []

    for translation in translations:
        if translation["rejected"]:
            continue
        render_lines += ["- \[EN\]: " + colored(translation["source"]["text"], "cyan")]

    if len(word_examples) != 0:
        render_lines += ["\n  \n\tExamples:"]
        for example in word_examples[:5]:
            example_word_associations = example["word_associations"]
            example_words = example["target_text"].split(" ")
            for i in range(len(example_word_associations)):
                if (
                    example_word_associations[i]["word"]["root_word"]["id"]
                    == word["id"]
                ):
                    example_words[i] = colored(
                        example_word_associations[i]["word"]["target_text"],
                        get_word_type_color(word["word_type"]["abbreviation"]),
                        attrs=["bold"],
                    )

            render_lines += ["\t- *" + (" ".join(example_words)).strip() + "*"]
            render_lines += [
                "\n\t\t" + colored(example["literal_source"], attrs=["dark"])
            ]

    rich_console.print(Markdown("\n".join(render_lines)))
    print()

    print("\n" + colored("TRANSLATIONS - faztaa's source: ", "white", attrs=["bold"]))
    translations = faztaa_first_result["content"][0]["means"]
    render_lines = []
    for translation in translations:
        render_lines += ["- \[EN\]: " + colored(translation["mean"], "cyan")]
        if len(translation["examples"]) == 0:
            continue

        render_lines += ["\n\tExamples:"]
        for example in translation["examples"][:5]:
            render_lines += [
                ("\t- _" + example["e"] + "_").replace(
                    word["target_text"],
                    colored(
                        word["target_text"],
                        get_word_type_color(word["word_type"]["abbreviation"]),
                        attrs=["bold"],
                    ),
                )
            ]
            render_lines += ["\n\t\t" + colored(example["m"], attrs=["dark"])]
    rich_console.print(Markdown("\n".join(render_lines)))
    print()

    # print verb conjugation -----------------------------------------------------
    if word["word_type"]["abbreviation"] == "vrb":
        verb_conjugations = word_resources["verb_conjugations"]

        print("\n" + colored("VERB CONJUGATION", "light_red", attrs=["bold"]))
        verb_conjugation_table = Table()
        verb_conjugation_table.add_column("PERSPECTIVE")

        conjugation_mappings = {
            "singular_1p": [],
            "singular_2p": [],
            "plural_2p": [],
            "singular_3p": [],
            "plural_1p": [],
        }

        for conjugation in verb_conjugations:
            verb_conjugation_table.add_column(conjugation["concept"]["name"])
            for key in conjugation_mappings.keys():
                conjugation_mappings[key] += [Text(conjugation[key], style="bold red")]

        verb_conjugation_table.add_row(
            "ich",
            *conjugation_mappings["singular_1p"],
        )
        verb_conjugation_table.add_row(
            "du",
            *conjugation_mappings["singular_2p"],
        )
        verb_conjugation_table.add_row(
            "ihr",
            *conjugation_mappings["plural_2p"],
        )
        verb_conjugation_table.add_row(
            "er/sie/es",
            *conjugation_mappings["singular_3p"],
        )
        verb_conjugation_table.add_row(
            "wir/sie/Sie/Sie",
            *conjugation_mappings["plural_1p"],
        )

        rich_console.print(verb_conjugation_table)
        print()

    # print external references --------------------------------------------------
    print()
    rich_console.print(
        Markdown(
            "**External References to Word definition:**\n"
            + "- **DWDS**:       "
            + f"https://www.dwds.de/wb/{word['target_text']}"
            + "\n"
            + "- **Wiktionary**: "
            + f"https://de.wiktionary.org/wiki/{word['target_text']}"
            + "\n"
            + "- **Collins**:    "
            + f"https://www.collinsdictionary.com/dictionary/german-english/{word['target_text']}"
            + "\n"
            + "- **Seedlang**:   "
            + f"https://seedlang.com/vocab/words/{word['id']}"
            + "\n"
            + "- **Faztaa**:     "
            + f"https://faztaa.com/search/word/{word['target_text']}?hl=en"
            + "\n"
            + "- **Cambridge**:  "
            + f"https://dictionary.cambridge.org/dictionary/german-english/{word['target_text']}"
            + "\n"
            + "- **Google Img**: "
            + f"https://www.google.com/search?q={word['target_text']}&udm=2"
            + "\n"
        )
    )

    # print helper command -------------------------------------------------------
    print()
    print("To quickly add the word to your deck, please use the following command:")
    print(
        "\t"
        + colored("python .\seedlang.py add-review", "white")
        + " "
        + colored(word_id, "cyan")
    )
    print()


@typer_app.command("add-review")
def add_to_review(word_id):
    res = add_word_to_reviews(word_id)

    rich_print(res)
    on_due_cards_stat = put(
        "https://seedlang.com/api/decks/59c08cb3-bdb7-447b-b573-fb68056463d8/cards_count",
        {
            "filters": {
                "card_type_id": None,
                "retired": False,
                "difficulty_label": None,
                "created_at_before_after": "after",
                "created_at_days_ago": None,
                "due": "past-due",
            }
        },
    )

    print()

    total_count = on_due_cards_stat["review_cards_count"]
    with Progress() as progress:
        t = progress.add_task("Wating for review: ", total=total_count)
        progress.update(t, advance=(on_due_cards_stat["count"]))

    print(
        colored(on_due_cards_stat["count"], "red", attrs=["bold"])
        + " / "
        + str(total_count)
        + " cards"
    )
    print()

    rich_print(
        "To quickly review, click here: "
        + "https://seedlang.com/reviews/decks/59c08cb3-bdb7-447b-b573-fb68056463d8"
    )


@typer_app.command("review")
def review():
    webbrowser.open(
        "https://seedlang.com/reviews/decks/59c08cb3-bdb7-447b-b573-fb68056463d8"
    )


# -----


@typer_app.command("dev-test")
def test(word_id):
    gather_parallel_word_details(word_id)


def main():
    print_list_word(1, hide_learned=False)


if __name__ == "__main__":
    init_cookie_map()
    typer_app()
