import numpy as np
import pandas as pd
from bs4 import BeautifulSoup as bs
import csv
from datetime import datetime, timedelta
import string
import re


def missing(text, i):
    """
    Checks if there are indicators of missing letters (e.g. "[3]").
    Takes in an inscription text as a string and an index i.
    Checks if at this index, the code is dealing with an indication
    of missing letters (e.g. "[3]" etc.), and if so, returns True.
    In all other cases, it returns False.
    """
    if i < len(text) - 2:
        if text[i] == '[' and text[i + 1].isnumeric() and text[i + 2] == ']':
            return True
        if text[i - 1] == '[' and text[i].isnumeric and text[i + 1] == ']':
            return True
        if text[i - 2] == '[' and text[i - 1].isnumeric() and text[i] == ']':
            return True
    return False


def correct_text(text):
    """
    Corrects ancient spelling errors in inscription text.
    Takes in the text of an inscription with corrected letters as a string.
    Searches for opening and corresponding closing angle brackets (<>),
    as well as all equal signs, adding them to a list each.
    For each of these pairs, the square brackets and the incorrect letter
    are removed from the text, and once all incorrect letters are removed,
    the cleaned text is returned.
    """
    corrected = ''
    opens = text.find("<")
    opening_list = []
    equals_list = []
    closing_list = []
    while opens != -1 and opens + 1 < len(text):
        equals = text.find("=", opens)
        closes = text.find(">", opens)
        opening_list.append(opens)
        equals_list.append(equals)
        closing_list.append(closes)
        opens = text.find("<", opens + 1)

    closing = 0
    for i in range(len(opening_list)):
        for j in range(closing, opening_list[i]):
            corrected += text[j]
        closing = closing_list[i] + 1
        for k in range(opening_list[i] + 1, equals_list[i]):
            corrected += text[k].lower()
    for x in range(closing, len(text)):
        corrected += text[x]
    return corrected


def remove_superficial_letters(text):
    """
    Removes ancient superficial letters from inscription text.
    Takes in the text of an inscription with superficial letters as a string.
    Searches for opening and matching closing curly braces ({}),
    adding them to a list each.
    For each of these pairs, the curly braces and whatever is within them
    are removed from the text, and once all superficial letters are removed,
    the cleaned text is returned.
    """
    result = ''
    opens = text.find('{')
    opening_list = []
    closing_list = []
    while opens != -1 and opens + 1 < len(text):
        closes = text.find('}', opens)
        opening_list.append(opens)
        closing_list.append(closes)
        opens = text.find('{', opens + 1)

    closing = 0
    for i in range(len(opening_list)):
        for j in range(closing, opening_list[i]):
            result += text[j]
        closing = closing_list[i] + 1
    for k in range(closing, len(text)):
        result += text[k]
    return result


def get_cleantext(text):
    """
    Parses inscription text and returns cleantext.
    Takes in the text of an inscription as a string.
    Searches for equal signs and curly braces (which indicate edits)
    and if found, corrects the text and / or removes superficial letters.
    Then, all 'inscriptionese' (e.g. '/', brackets, etc.) is removed,
    and all spaces, characters, and missing indicators (i.e. "[3]" etc.)
    are added to the result, which is split at whitespace,
    and joined with a whitespace, and then returned.
    """
    result = ''
    equals = text.find('=')  # text contains corrected letters
    curly = text.find('{')  # text contains superficial letters
    if equals != -1:  # text contains corrected letters
        text = correct_text(text)
    if curly != -1:  # text contains superficial letters
        text = remove_superficial_letters(text)
    for i in range(len(text)):  # remove all inscriptionese (e.g. '/', brackets)
        if text[i].isspace() or text[i].isalpha() or missing(text, i):
            result += text[i]
    result = " ".join(result.split())
    return result


def get_lat(place):
    """
    Extracts the latitude from the place-link.
    Takes in some html code with details about the findspot.
    Searches for the latitude-tag.
    From the end of it until the end of the string, appends
    all numeric characters, full stops, and minus signs to the result.
    Once something else is found, tries to return result as float or string.
    """
    result = ''
    start = place.find("latitude=")
    if start == -1:
        return np.nan
    for i in range(start + 9, len(place)):
        if place[i].isnumeric() or place[i] == "." or place[i] == "-":
            result += place[i]
        else:
            try:
                return float(result)
            except ValueError:
                return result


def get_long(place):
    """
    Extracts the longitude from the place-link.
    Takes in some html code with details about the findspot.
    Searches for the latitude-tag.
    From the end of it until the end of the string, appends
    all numeric characters, full stops, and minus signs to the result.
    Once something else is found, tries to return result as float or string.
    """
    result = ''
    start = place.find("longitude=")
    if start == -1:
        return np.nan
    for i in range(start + 10, len(place)):
        if place[i].isnumeric() or place[i] == "." or place[i] == "-":
            result += place[i]
        else:
            try:
                return float(result)
            except ValueError:
                return result


def get_date(snippet, smallest):
    """
    Extracts the smallest or largest number from a dictionary.
    Takes in a dictionary containing a snippet of an inscriptions.
    Tries to convert each element to an integer and add it to a list.
    From each successful try, the smallest or largest element is returned,
    depending on what is searched.
    """
    numbers = []
    for elem in snippet:
        try:
            elem = re.sub(r'\D', '', elem)
            numbers.append(int(elem))
        except ValueError:
            pass
    if numbers:
        if smallest:
            return min(numbers)
        return max(numbers)
    print(snippet)
    return np.nan


def get_insc_dict(inscs):
    """
    Transforms each inscription into a dict and combines all to master dict
    Takes in the list of inscriptions, each as a list itself.
    For each inscription (each list element), the function matches each element
    to a dictionary.
    Creates master dictionary and adds all inscriptions as elements.
    Returns master dictionary.
    """
    insc_dict = {}
    total = len(inscs)
    # loop over all inscriptions in list
    for i, insc in enumerate(inscs):
        if i > 0 and i % 10000 == 0:
            print(f'Added to dictionary: {i} inscriptions (ca. ',
                  f'{round(100 / total * i, 2)}%)')
        # check if inscription has a EDCS-ID. If not, continue with next.
        if "EDCS-ID:" not in insc:
            continue
        edcs_id = ''
        # create dictionary for inscription
        inscription = {
            "publication": "n/a",
            "edcs-id": np.nan,
            "time_from": np.nan,
            "time_to": np.nan,
            "province": "n/a",
            "findspot": "n/a",
            "find_lat": np.nan,
            "find_long": np.nan,
            "text": "n/a",
            "cleantext": "n/a",
            "keywords": "n/a",
            "material": "n/a",
            "comment": "n/a",
        }
        # iterate over inscription elements; add matching ones to dictionary.
        for idx, elem in enumerate(insc):
            match elem:
                case 'Publikation:':
                    inscription["publication"] = insc[idx + 1]
                case 'Datierung:':
                    # assume multiple dates are available: find extremes
                    snippet = insc[idx:insc.index('EDCS-ID:')]
                    inscription["time_from"] = get_date(snippet, True)
                    inscription["time_to"] = get_date(snippet, False)
                case 'EDCS-ID:':
                    edcs_id = insc[idx + 1]
                    inscription["edcs-id"] = edcs_id
                case 'Provinz:':
                    inscription["province"] = insc[idx + 1]
                case 'Ort:':
                    # check if there is a comment with the coordinates
                    if '<!--' == insc[idx + 1][:4]:
                        # if there is comment, findspot is just after that
                        inscription["findspot"] = insc[idx + 2]
                        # extract coordinates if there is a comment
                        place = insc[idx + 1]
                        inscription["find_lat"] = get_lat(place)
                        inscription["find_long"] = get_long(place)
                        # text is always element after findspot
                        inscription["text"] = insc[idx + 4]
                    else:
                        # if no comment, findspot just after 'Ort:'
                        inscription["findspot"] = insc[idx + 1]
                        # text is always element after findspot
                        inscription["text"] = insc[idx + 2]
                case 'Inschriftengattung / Personenstatus:':
                    inscription["keywords"] = insc[idx + 1]
                    # if text has not yet been found, add it.
                    if inscription["text"] == 'n/a':
                        inscription["text"] = insc[idx - 1]
                case 'Material:':
                    inscription["material"] = insc[idx + 1]
                    # if text has not yet been found, add it.
                    if inscription["text"] == 'n/a' and \
                            inscription["keywords"] == 'n/a':
                        inscription["text"] = insc[idx - 1]
                case 'Kommentar' | 'Kommentar:':  # both exist in EDCS
                    # if comment contains link or consists of mult. paragraphs,
                    # it is scraped as multiple elements or inscriptions
                    comment_list = []
                    for j in range(1, 100):
                        if idx + j < len(insc):
                            comment_list.append(insc[idx + j])
                        else:
                            break
                    # check if next 'inscription' is actually continued comment
                    for k in range(1, 100):
                        if i + k < len(inscs) and 'EDCS-ID:' not in inscs[i + k]:
                            # if not, add all 'inscriptions' to comment,
                            # until real inscription is found.
                            for element in inscs[i + k]:
                                comment_list.append(element)
                        else:
                            break
                    # add all comment elements to comment
                    inscription["comment"] = ' '.join(comment_list)
            # create cleantext from raw text
            inscription["cleantext"] = get_cleantext(inscription["text"])
        # add inscription to dictionary of all inscriptions
        insc_dict[edcs_id] = inscription
    print(f'Dictionary completed containing {len(insc_dict)} inscriptions.')
    return insc_dict


def clean(insc):
    """
    Cleans the sourcetext of one inscription into workable list.
    Takes in the html sourcetext of an inscription.
    Parses the html using beautifulsoup,
    and creates a content variable containing all text without tags.
    For each element in content, if it is not a line break, empty,
    a colon, or the EDCS-ID, the element is stripped of non-breaking spaces,
    split at whitespace, and joined with a whitespace.
    If the element now is not empty, it is appended to a result,
    and once all elements in content are cleaned, result is returned.
    """
    soup = bs(insc, 'html.parser')
    content = soup.find_all(text=True)
    result = []
    for element in content:
        if not element == '\n' and not element == ' ' and not element == ':':
            nelement = element.replace("\xa0", "")
            melement = " ".join(nelement.split())
            if melement != '':
                result.append(melement)
    return result


def get_list(sourcetext):
    """
    Creates a list of inscriptions from sourcetext.
    Takes in the sourcetext as raw html.
    Splits sourcetext at '</p>'-tag, as each new inscription
    is encoded as a paragraph in the EDCS.
    If element is not empty, it is cleaned using the clean-function,
    and then appended to a list of inscriptions.
    As this takes a long time, progress is printed
    to the console once every 1000 inscriptions.
    When done, returns the list with all inscriptions.
    """
    inscs = sourcetext.split('</p>')
    print("Inscriptions split")
    inscs_cleaned = []
    counter = 0
    total = len(inscs)
    for insc in inscs:
        # check if empty or search-metadata; if so, continue with next insc
        if insc == '' or 'Gefundene Inschriften:' in insc:
            continue
        cleaned = clean(insc)
        if cleaned:
            inscs_cleaned.append(cleaned)
        counter += 1
        if counter % 1000 == 0:
            print(f'Included in list: {counter} inscriptions ',
                  f'(ca. {round(100 / total * counter, 2)}%)')
    print(f'Created inscription list containing {len(inscs_cleaned)} items.')
    return inscs_cleaned


def save_list(inscriptions, today):
    """
    Saves the list of inscriptions to a csv.
    """
    name = "EDCS_InscList_" + today.strftime('%Y-%m-%d') + ".csv"
    with open(name, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(inscriptions)
        print(f"CSV from InscriptionList created: {name}.")


def open_list(date):
    """
    Opens list of inscriptions from csv.
    """
    searching = True
    while searching:
        date_str = date.strftime('%Y-%m-%d')
        filename = 'EDCS_InscList_' + date_str + '.csv'
        try:
            with open(filename, newline="", encoding='utf-8') as f:
                reader = csv.reader(f)
                insc_list = list(reader)
                searching = False
        except FileNotFoundError:
            date = (date - timedelta(days=1))
    print(f"Read inscription list: {filename}.")
    return insc_list


def open_sourcecode(date):
    """
    Starting from today, looks for the most recent version of the
    EDCS sourcecode ('EDCS_HTML_allprovinces_DATE.txt').
    Once found, opens and returns it.
    """
    searching = True
    while searching:
        date_str = date.strftime('%Y-%m-%d')
        filename = 'EDCS_HTML_allprovinces_' + date_str + '.txt'
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                sourcecode = f.read()
            searching = False
        except FileNotFoundError:
            date = (date - timedelta(days=1))
    print(f"Read EDCS sourcecode: {filename}.")
    return sourcecode


def create_csv(inscription_dict, today):
    """
    Takes in the dictionary of inscriptions.
    Saves it to a csv.
    """
    name = "EDCS_complete_" + today.strftime('%Y-%m-%d') + ".csv"
    output = pd.DataFrame(inscription_dict)
    output = output.transpose()
    output.to_csv(name, index=False)
    print(f"CSV of EDCS created: {name}.")


def main():
    today = datetime.today()

    # get sourcetext from file
    sourcetext = open_sourcecode(today)

    # transform sourcetext to a list of all inscriptions (each as a list itself)
    inscriptions = get_list(sourcetext)

    # save inscription list to a csv
    save_list(inscriptions, today)

    # transform list of all inscriptions to a dictionary of inscriptions
    inscription_dict = get_insc_dict(inscriptions)

    # save EDCS to a CSV
    create_csv(inscription_dict, today)


if __name__ == '__main__':
    main()
