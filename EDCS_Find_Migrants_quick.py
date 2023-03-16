import re
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import requests
import urllib3
import haversine as hs


def open_database(name, date):
    """
    Opens csv database and returns it as a pandas dataframe.
    Takes in the name of the database and today's date.
    Searches for the most recent version of the database; returns it.
    """
    searching = True
    while searching:
        date_str = date.strftime('%Y-%m-%d')
        filename = f"{name}{date_str}.csv"
        try:
            database = pd.read_csv(filename)
            searching = False
        except FileNotFoundError:
            date = (date - timedelta(days=1))
    print(f"read database {filename}.")
    return database


def save_database(database, today, name):
    """
    Takes in a pandas dataframe, today's date, a name_tag, and a bool (idx).
    Saves it using the name-tag and date as a csv, with or without index.
    """
    filename = f"{name}_{today.strftime('%Y-%m-%d')}.csv"
    database.to_csv(filename, index=False, encoding="utf-8")
    print(f"Saved {name} database to csv.")


def get_legal_status(row):
    """
    Takes in a row of the migrants dataframe.
    Loops over the cleantext, checking each word as to whether it is indicative
    of legal status. The first such word determines the legal status, and
    a corresponding number is returned.
    """
    slave = ['servus', 'servi', 'servo', 'servum', 'servom', 'servorum',
             'servis', 'servos', 'serva', 'servae', 'servai', 'servam',
             'servarum', 'servas', 'servabus']
    freed = ['libertus', 'liberti', 'liberto', 'libertum', 'libertom',
             'liberte', 'libertorum', 'libertis', 'libertos', 'liberta',
             'libertae', 'libertai', 'libertam', 'libertad', 'libertarum',
             'libertabus']  # without 'libertas'
    free = ['filia', 'filiae', 'filiai', 'filiam', 'filiad', 'filiarum',
            'filiabus', 'filias', 'filius', 'fili', 'filii', 'filio',
            'filium', 'filiom', 'filiorum', 'filios']
    if isinstance(row['cleantext'], str):
        words = row['cleantext'].split()
        for word in words:
            if word.lower() in slave:
                return 0
            if word.lower() in freed:
                return 1
            if word.lower() in free:
                return 2
    return -1


def add_status(edcs):
    text = edcs['cleantext']

    slave = r'\bserv(?:us|i|o|um|om|orum|is|os|a|ae|ai|am|arum|as|abus)\b'
    edcs['slave'] = np.where(text.str.contains(slave, regex=True), 1, 0)

    # without libertas
    lib = r'\blibert(?:us|i|o|um|om|e|orum|is|os|a|ae|ai|am|ad|arum|abus)\b'
    edcs['freed'] = np.where(text.str.contains(lib, regex=True), 1, 0)

    free = r'\bfili(?:us|i|o|um|om|orum|is|os|a|ae|ai|am|ad|arum|abus|as)\b'
    edcs['freeborn'] = np.where(text.str.contains(free, regex=True), 1, 0)

    edcs['legal_status'] = edcs.apply(lambda row: get_legal_status(row), axis=1)
    return edcs


def no_tags(elem):
    """
    Takes in a string.
    Searches for opening angle bracket ("<"). If none is found, returns string.
    If brackets are found, searches for corresponding closing bracket,
    removes everything in between (=tag), and starts again.
    Returns string without tags.
    """
    opening = elem.find("<")
    while opening != -1:
        closing = elem.find(">")
        remove = elem[opening:closing + 1]
        elem = elem.replace(remove, "")
        opening = elem.find("<")
    return elem


def get_name_set():
    """
    Returns a set of all names from the Prosopographia Imperii Romani database.
    Opens PIR database and creates a name_set with common abbreviated names.
    Each name in the PIR database is cleaned up and added to the name_set.
    Returns name_set.
    """
    url = 'https://github.com/telota/PIR/raw/public/data/' \
          'pir_export_2021-05-07.csv'
    pir = pd.read_csv(url)
    name_set = {"Aulus", "Appius", "Gaius", "Gnaeus", "Decimus", "Lucius",
                "Marcus", "Manius", "Publius", "Quintus", "Sergius", "Sextus",
                "Spurius", "Titus", "Tiberius", "Aelia", "Aelius", "Aurelia",
                "Aurelius", "Claudia", "Claudius", "Flavia", "Flavius",
                "Iulia", "Iulius", "Valeria", "Valerius", "Caius", "Cnaeus"}
    for idx, name in enumerate(pir['annotated']):
        name = no_tags(name)
        no_words = {"...", "..", "(", ")", "[", "]", "-", "?"}
        for elem in no_words:
            name = name.replace(elem, "")
        name = name.replace("vel", " ")
        parts = name.split()
        for part in parts:
            if part[-1] != "." and part[0].isupper() and len(part) > 3:
                name_set.add(part)
    return name_set


def get_name(row, name_set):
    """
    Takes in a series (=row) of a pandas dataframe containing one inscription
    and the list of all names in the PIR.
    For each word in the cleantext which is sufficiently long, starts with a
    capital letter, and is not in the non_names list, the word is converted
    to its nominative case, and then looked up in the word list.
    Each match is attached to a string, which is finally returned.
    """
    names = ""
    words = row['cleantext']
    if isinstance(words, str):
        words = row['cleantext'].split()
        non_names = ["Dis", "Manibus"]
        for word in words:
            try:
                word.encode('ascii')
            except UnicodeEncodeError:  # contains Greek / non-Latin letters
                continue
            if len(word) > 2 and word[0].isupper() and word[1].islower() and \
                    word not in non_names:
                if word[-2:] == "ae":
                    word = word[:-1]
                elif word[-1] == "i" or word[-1] == "o":
                    word = word[:-1] + "us"
            if word in name_set:
                names += word + ", "
        if "," in names:
            names = names[:-2]
    return names


def get_gender_person(row):
    """
    Takes in a series (=row) of a pandas dataframe containing one inscription.
    If row does not contain a name, returns -1.
    Else, it loops over all names, looking if they are most likely male ("-us")
    or female ("-a"), and if the ratio between male and female names is
    sufficiently clear, returns probable gender (0=male, 1=female, 2=unclear).
    """
    if row['contains_name'] == 0:
        return -1
    male = 0
    female = 0
    male_names = {"Agrippa", "Aquila", "Caracalla", "Nerva", "Scaevola",
                  "Seneca"}
    male_suffix = {"us"}
    names = row['name'].split()
    for name in names:
        name = name.replace(",", "").strip()
        if name[-2:] in male_suffix or name in male_names or \
                (name[-2:] == "is" and name[-5:] != "ensis"):
            male += 1
        elif (name[-1] == "a" or name[-2:] == "oe") and name not in male_names:
            female += 1
    if male > 0 and female == 0:
        return 0
    elif male == 0 and female > 0:
        return 1
    elif male == 0 and female == 0:
        return -1
    else:
        if male / female >= 2:
            return 0
        elif female / male >= 2:
            return 1
        else:
            return -1


def get_gender_keywords(row):
    if row['m'] == 1 and row['f'] == 0:
        return 0
    elif row['f'] == 1 and row['m'] == 0:
        return 1
    else:
        return -1


def gender_firstword(row):
    """
    Returns the gender of the first capitalised word of the cleantext.
    Takes in a row of the EDCS. Looks at each Capitalised word.
    If Word can be assigned a gender, returns gender (0=male, 1=female).
    If no such words, returns -1.
    """
    non_names = {"Dis", "Manibus"}
    male_names = {"Agrippa", "Aquila", "Caracalla", "Nerva", "Scaevola",
                  "Seneca"}
    male_suffix = {"us", "os", "is", "er", "i", "o"}
    words = row['cleantext']
    if isinstance(words, str):
        words = row['cleantext'].split()
        for word in words:
            try:
                word.encode('ascii')
            except UnicodeEncodeError:  # contains Greek / non-Latin letters
                continue
            if len(word) > 2 and word[0].isupper() and \
                    word[1].islower() and word not in non_names:
                if word in male_names or word[-2:] in male_suffix or \
                        word[-1] in male_suffix:
                    return 0
                elif word[-2:] == "ae" or word[-1] == "a":
                    return 1
    return -1


def get_gender_ensis(row):
    """
    Takes in a row of a pandas dataframe.
    Loops over cleantext, looking for words indicating origin (e.g.'-ensis').
    If found, searches from that word backwards for a name.
    If found, assigns & returns gender on the basis of that name.
    If either not found, returns -1.
    """
    if not isinstance(row['cleantext'], str):
        return -1

    start = None
    name = ""
    words = row['cleantext'].split()
    locs = r'\b\w*ens(?:is|i|em|e|es|ium|ia|ibus)\b|' \
           r'\b\w*itan(?:us|i|o|um|a|ae|am|is|os|as|orum|arum)\b|' \
           r'\b\w*an(?:us|i|o|um|a|ae|am|orum|os|is|arum|as)\b|' \
           r'\b\w*ian(?:us|i|o|um|a|ae|am|orum|os|is|arum|as)\b' \
           r'\b\w*gn(?:us|i|o|um|a|ae|am|orum|os|is|arum|as)\b|' \
           r'\btrib(?:us|ui|um|u|uum|ibus)\b|' \
           r'\bciv(?:is|i|em|e|es|ium|ibus)\b|' \
           r'\bdomo\b|\borigo\b|\bnatione\b|' \
           r'\bcoloni(?:a|ae|am|arum|is|as)\b'

    for idx, word in enumerate(words):
        match = re.search(locs, word)
        if match:
            start = idx
            break

    if start is not None:
        non_names = {"Dis", "Manibus"}
        for i in reversed(range(start)):
            if words[i][0].isupper() and len(words[i]) > 2 and \
                    words[i][1].islower() and words[i] not in non_names:
                name = words[i]
                break

    if len(name) > 2:
        male_n = {"Agrippa", "Aquila", "Caracalla", "Nerva", "Scaevola",
                  "Seneca"}
        male_s = {"us", "os", "is", "er", "i", "o"}
        if name in male_n or name[-2:] in male_s or name[-1] in male_s:
            return 0
        elif name[-2:] == "ae" or name[-1] == "a":
            return 1
    return -1


def get_filix(row):
    """
    Assigns the gender of an inscription based on filiation.
    Takes in a row of a pandas dataframe.
    Loops over each word of the inscription text ("cleantext"), searching if
    a filiation can be found. If yes, determines gender accordingly and
    returns 0 for male and 1 for female forms.
    """
    female = ['filia', 'filiae', 'filiai', 'filiam', 'filiad', 'filiarum',
              'filiabus', 'filias']
    male = ['filius', 'fili', 'filii', 'filio', 'filium', 'filiom', 'filiorum',
            'filios']
    if not isinstance(row['cleantext'], str):
        return -1
    words = row['cleantext'].split()
    for word in words:
        if word.lower() in female:
            return 1
        elif word.lower() in male:
            return 0
    return -1


def get_servx(row):
    """
    Assigns the gender of an inscription based on servile indicator.
    Takes in a row of a pandas dataframe.
    Loops over each word of the inscription text ("cleantext"), searching if a
    servile indicator can be found. If yes, determines gender accordingly and
    returns 0 for male and 1 for female forms.
    """
    female = ['serva', 'servae', 'servam', 'servarum', 'servabus', 'servas',
              'servai']  # without 'servis'
    male = ['servus', 'servi', 'servo', 'servum', 'serve', 'servorum', 'servos',
            'servom']  # without 'servis'
    if not isinstance(row['cleantext'], str):
        return None
    words = row['cleantext'].split()
    for word in words:
        if word.lower() in female:
            return 1
        elif word.lower() in male:
            return 0
    return -1


def add_gender(edcs):
    """
    Determines the gender of the dedicatee of each inscription.
    Takes in the EDCS database; assigns each inscription a gender using
    different methods.
    Returns EDCS with added gender metadata.
    """
    name_set = get_name_set()
    edcs['name'] = edcs.apply(lambda row: get_name(row, name_set), axis=1)
    edcs['contains_name'] = np.where(edcs['name'].str.len() > 2, 1, 0)

    edcs['gender_main_pers'] = edcs.apply(lambda row: get_gender_person(row),
                                          axis=1)
    edcs['viri'] = np.where(edcs['keywords'].str.contains('vir'), 1, 0)
    edcs['mulieres'] = np.where(edcs['keywords'].str.contains('mulier'), 1, 0)
    edcs['m'] = np.where((edcs['viri'] == 1) |
                         (edcs['gender_main_pers'] == 0), 1, 0)
    edcs['f'] = np.where((edcs['mulieres'] == 1) |
                         (edcs['gender_main_pers'] == 1), 1, 0)

    edcs['gender_keywords'] = edcs.apply(lambda row: get_gender_keywords(row),
                                         axis=1)
    edcs['gender_of_1st_Word'] = edcs.apply(lambda row: gender_firstword(row),
                                            axis=1)
    edcs['gender_ensis'] = edcs.apply(lambda row: get_gender_ensis(row), axis=1)
    edcs['gender_filix'] = edcs.apply(lambda row: get_filix(row), axis=1)
    edcs['gender_servx'] = edcs.apply(lambda row: get_servx(row), axis=1)
    return edcs


def assign_gender(row):
    """
    Assigns gender of inscription based on gender-determining tests.
    For each row in the EDCS, checks if any of the good tests found a gender.
    In order of their predictive power (where 'gender_keywords is correct in
    ca. 94%, filix and servx together in ca. 90%, and the first capitalised
    word in ca. 83% of all cases), returns gender of inscription.
    """
    if row['gender_keywords'] == 0 or row['gender_filix'] == 0 or \
            row['gender_servx'] == 0 or row['gender_of_1st_Word'] == 0:
        return 'm'
    elif row['gender_keywords'] == 1 or row['gender_filix'] == 1 or \
            row['gender_servx'] == 1 or row['gender_of_1st_Word'] == 1:
        return 'f'
    else:
        return None


def add_metadata(edcs):
    """
    Adds gender, social & legal status, funerary and migrant metadata to edcs.
    Returns EDCS containing metadata.
    """
    edcs = add_gender(edcs)
    edcs['gender'] = edcs.apply(lambda row: assign_gender(row), axis=1)

    edcs = add_status(edcs)
    edcs['text_length'] = edcs['cleantext'].str.len()

    text = edcs['cleantext'].str.lower()
    regex = r'faciend(?:[a-z]+) curav(?:[a-z]+)|dis manibus|' \
            r'sit(?:[a-z]+) est|bene merenti|vixit|ex testamento|' \
            r'sit tibi terra levis|requiesc[a-z]t'
    edcs['funerary'] = np.where(edcs['keywords'].str.contains("sepulcrales") |
                                text.str.contains(regex, regex=True),
                                1, 0)

    # \b word boundary, \w* one or more word chars, (?:x|y)\b ends in x or y
    locs = r'\b\w*ens(?:is|i|em|e|es|ium|ia|ibus)\b|' \
           r'\b\w*itan(?:us|i|o|um|a|ae|am|is|os|as|orum|arum)\b|' \
           r'\b\w*an(?:us|i|o|um|a|ae|am|orum|os|is|arum|as)\b|' \
           r'\b\w*ian(?:us|i|o|um|a|ae|am|orum|os|is|arum|as)\b' \
           r'\b\w*gn(?:us|i|o|um|a|ae|am|orum|os|is|arum|as)\b|' \
           r'\btrib(?:us|ui|um|u|uum|ibus)\b|' \
           r'\bciv(?:is|i|em|e|es|ium|ibus)\b|' \
           r'\bdomo\b|\borigo\b|\bnatione\b|' \
           r'\bcoloni(?:a|ae|am|arum|is|as)\b'
    # r'\b\w*in(?:us|i|o|um|a|ae|am|orum|os|is|arum|as)\b|' \
    # r'\b\w*ic(?:us|i|o|um|a|ae|am|orum|os|is|arum|as)\b|' \
    edcs['location_indicator'] = np.where(text.str.contains(locs, regex=True),
                                          1, 0)
    return edcs


def no_brackets(elem):
    """
    Takes in a string.
    Searches for opening or closing parentheses. If none found, returns string.
    If found, checks if it is an omission ("(...)"), and if so, removes it;
    checks if it is an entire word, and if so, removes it;
    if it is neither (i.e. a spelling variant), creates both readings.
    Repeats until no more parentheses are found.
    Returns string without all elements in parentheses.
    """
    opening = elem.find("(")
    variants = False
    while opening != -1:
        closing = elem.find(")", opening)
        remove = elem[opening:closing + 1]
        if remove == "(...)":
            elem = elem.replace(remove, "")
        elif opening > 0 and elem[opening - 1].isspace():
            remove = elem[opening:closing + 1]
            elem = elem.replace(remove, "")
        else:
            variants = True
        opening = elem.find("(", opening + 1)
    elem = elem.replace("  ", " ").replace(" ,", ",")

    if variants:
        result = []
        words = elem.split(" ")
        for word in words:
            opening = word.find("(")
            if opening == -1:
                result.append(word)
            while opening != -1:
                closing = word.find(")", opening)
                variant = word[opening:closing + 1]
                word_without = word.replace(variant, "")
                result.append(word_without)
                word_with = word.replace("(", "").replace(")", "")
                result.append(word_with)
                opening = word.find("(", opening + 1)
        elem = " ".join(result)
    return elem


def get_place_names(pleiades):
    """
    Takes in a pandas dataframe with the Pleiades names database.
    Creates a new column 'placenames'.
    For each location, removes html-tags, comments in brackets,
    checks for variants, and adds all variants 'placenames' column.
    Returns dataframe.
    """
    pleiades['placenames'] = None
    ancient = "HRL"
    for idx, elem in pleiades.iterrows():
        relevant = False
        try:
            for letter in elem['timePeriods']:
                if letter in ancient:
                    relevant = True
                    break
        except TypeError:
            relevant = True
        if not relevant:
            continue
        place_names = set()
        elem = no_tags(elem['nameTransliterated'])
        elem = elem.replace("?", "").replace('[', '').replace(']', '')
        elem = no_brackets(elem)
        comma = elem.find(",")
        if comma == -1:
            place_names.add(elem.replace("  ", " ").strip())
        else:
            locs = elem.split(",")
            for loc in locs:
                slash = loc.find("/")
                if slash == -1:
                    place_names.add(loc.replace("  ", " ").strip())
                else:
                    loks = loc.split("/")
                    for lok in loks:
                        place_names.add(lok.replace("  ", " ").strip())
        # remove Castr, Fret and Misen
        if 'Castr' in place_names:
            place_names.remove('Castr')
        if 'Fret' in place_names:
            place_names.remove('Fret')
        if 'Misen' in place_names:
            place_names.remove('Misen')
        places = ", ".join(place_names)
        pleiades.at[idx, 'placenames'] = places
    print("Added column with placenames to Pleiades database.")
    return pleiades


def add_coordinates(pleiades):
    """
    Adds missing gps coordinates to the pleiades dump file.
    Takes in a pandas dataframe containing the Pleiades names database.
    Iterates over all rows, checking if row contains coordinates.
    If not, connects to the Pleiades API, downloads and adds them.
    Because there are some errors in the JSON files, the whole is wrapped
    in a try-except block and prints the index of all rows causing errors.
    Returns the thus modified dataframe.
    """
    # improved gps coordinate availability by some 16%.
    base_url = "https://pleiades.stoa.org"
    fixed = 0
    errors = []
    for idx, elem in pleiades.iterrows():
        if idx != 0 and idx % 100 == 0:
            print(f"Checked {idx} entries in database",
                  f"(ca. {round(100 / len(pleiades) * idx, 2)}%).",
                  f"Fixed {fixed} entries so far.")
        if isinstance(elem['reprLatLong'], float):
            try:
                url = base_url + elem['pid'] + "/json"
                response = requests.get(url)
                data = response.json()
                if 'reprPoint' in data.keys() and data['reprPoint']:
                    long = data['reprPoint'][0]
                    lat = data['reprPoint'][1]
                elif 'features' in data.keys() and data['features'] and \
                        'geometry' in data['features'][0].keys() and \
                        data['features'][0]['geometry'] is not None and \
                        'type' in data['features'][0]['geometry'].keys() and \
                        data['features'][0]['geometry']['type'] == 'Point':
                    coordinates = data['features'][0]['geometry']['coordinates']
                    long = coordinates[0]
                    lat = coordinates[1]
                else:
                    continue
                pleiades.at[idx, 'reprLat'] = lat
                pleiades.at[idx, 'reprLong'] = long
                pleiades.at[idx, 'reprLatLong'] = str(lat) + "," + str(long)
                fixed += 1
            except (TypeError, ValueError,
                    requests.exceptions.ChunkedEncodingError,
                    urllib3.exceptions.ProtocolError,
                    urllib3.exceptions.InvalidChunkLength):
                errors.append(f"{idx}, {elem['pid']}")
    with open('pleiades_coordinates_errors.txt', 'w', encoding='utf-8') as f:
        for elem in errors:
            f.write(str(elem) + '\n')
    print("Added missing coordinates to Pleiades database.")
    return pleiades


def add_stem(row):
    """
    Creates toponym-ready stems for each place in the Pleiades database.
    Takes in a row of the Pleiades database.
    Loops over the 'placenames' column, and if there is a placename,
    splits it at spaces. Loops backward over each such word until first vowel,
    and copies the stem into a list. If last letter of stem is a vowel,
    goes back one letter to create toponym-stem until a consonant is reached.
    Joins toponym-stem-list to a string, and returns it.
    """
    if row['placenames'] is None:
        return None
    vowels = "aeiou"
    stem_list = []
    locations = row['placenames'].split()
    for location in locations:
        for index, letter in enumerate(reversed(location)):
            if letter in vowels:
                i = len(location) - index - 1
                if i <= 2:
                    break
                else:
                    stem_list.append(location[:i])
                    while location[i - 1] in vowels:
                        stem_list.append(location[:i - 1])
                        i -= 1
                    break
    stems = ", ".join(stem_list)
    return stems


def find_migrants(edcs, pleiades):
    """
    Finds possible migrants in EDCS database based on Pleiades names.
    Takes in two dataframes: the EDCS and the modified Pleiades database.
    Creates a dataframe for migrants with same columns as EDCS.
    Loops over toponyms, and for each toponym, loops over the EDCS, searching
    if there is a match within the inscription text.
    If match is found, the respective line from the EDCS is copied to the
    migrants database, and toponym, GPS coordinates, and Pleiades ID is added.
    Once all toponyms have been searched for in all inscriptions,
    returns migrants database.
    """
    today = datetime.today()
    edcs.rename(columns={'edcs-id': 'edcs_id'}, inplace=True)
    edcs = edcs[edcs['funerary'] == 1]
    column_names = edcs.columns.values.tolist()
    migrants = pd.DataFrame(columns=column_names)
    r = 0
    found = 0
    length = len(pleiades)
    # remove Castrensis, Misenensis and Fretensis from stems
    pleiades['stem'] = pleiades['stem'].str.replace('Castr', '')
    pleiades['stem'] = pleiades['stem'].str.replace('Misen', '')
    pleiades['stem'] = pleiades['stem'].str.replace('Fret', '')
    # loop over Pleiades database, looking at each toponym stem
    for row in pleiades.itertuples():
        idx = row.Index
        if idx > 0 and idx % 10 == 0:
            print(f"Searched {idx} toponyms " +
                  f"(ca. {round(100 / length * idx, 2)}%). " +
                  f"Found {found} possible migrants so far.")
        # if there is no stem, continue to next row
        if not isinstance(row.stem, str):
            continue
        stems = [stem.strip() for stem in row.stem.split(",")]
        # search for words like 'Emeritensis', 'Coritanus', etc.
        for stem in stems:
            for insc in edcs.itertuples():
                if isinstance(insc.cleantext, float):
                    continue
                matches = []
                loc = r'\b{}ens(?:is|i|em|e|es|ium|ia|ibus)\b'.format(stem)
                for match in re.findall(loc, insc.cleantext):
                    matches.append(match)
                # if toponym is found, copy inscription to migrants database
                if matches:
                    migrants = pd.concat([migrants, pd.DataFrame([insc])], ignore_index=True)
                    # migrants = migrants.append(pd.DataFrame([row], columns=row._fields), ignore_index=True)
                    # migrants = pd.concat([migrants, insc],
                                          # pd.DataFrame(edcs.iloc[i]).T],
                                         # ignore_index=True)
                    migrants.at[r, 'origo'] = row.title
                    migrants.at[r, 'toponym'] = ",".join(matches)
                    migrants.at[r, 'origo_lat'] = row.reprLat
                    migrants.at[r, 'origo_long'] = row.reprLong
                    migrants.at[r, 'origo_LatLong'] = row.reprLatLong
                    migrants.at[r, 'path'] = row.path
                    migrants.at[r, 'pid'] = row.pid
                    migrants.at[r, 'pleiades'] = 1
                    if isinstance(migrants['origo_LatLong'].iloc[r], str) and \
                            len(migrants['origo_LatLong'].iloc[r]) >= 1:
                        migrants.at[r, 'located'] = 1
                    else:
                        migrants.at[r, 'located'] = 0
                    r += 1
                    found += 1
    save_database(migrants, today, 'EDCS_Migrants_quick_Raw01')
    migrants.index.name = "Index"
    # remove rows which have identical inscription and origo
    migrants.drop_duplicates(subset=['edcs_id', 'origo_LatLong'], inplace=True)

    print("Searched all toponyms; " +
          f"migrants database created containing {len(migrants)} entries.")
    return migrants


def remove_nonmigrants(migrants):
    """
    Removes the false-positives from the Migrants-databse.
    Takes in the migrants database. Removes all those entries which have a
    lowercase toponym or a toponym which equals 'Mens*'.
    Returns modified dataframe.
    """
    # delete the lowercase-match-migrants (mostly 'menses' and 'castrensis')
    regex = r'\b(?:[a-z]+)\b'
    delete = migrants['toponym'].str.contains(regex)
    migrants = migrants[~delete]

    # delete the 'Mense'- and 'Mensibus'-migrants
    pattern = r'\bMens(?:[a-z]+)\b'
    remove = migrants['toponym'].str.contains(pattern)
    migrants = migrants[~remove]
    return migrants


def round_distances(migrants):
    migrants['origo_lat'] = round(migrants['origo_lat'], 3)
    migrants['origo_long'] = round(migrants['origo_long'], 3)
    migrants['find_lat'] = round(migrants['find_lat'], 3)
    migrants['find_long'] = round(migrants['find_long'], 3)
    return migrants


def add_distance(row):
    """
    Adds the distance between findspot and origo to Migrants database.
    Takes in a dataframe row. If 'origo_LatLong' contains coordinates,
    calculates the distance between origo and findspot and returns it if > 10km.
    If 'origo_LatLong' doesn't contain coordinates, returns NaN.
    """
    if isinstance(row['origo_LatLong'], str):
        findspot = (row['find_lat'], row['find_long'])
        origo = (row['origo_lat'], row['origo_long'])
        distance = hs.haversine(findspot, origo)
        if distance > 10:  # prevent trivial distances and gps precision errors
            return distance
    return np.nan


def remove_duplicates(migrants):
    """
    Takes in a pandas dataframe containing the migrant database.
    Removes all duplicate migrants, keeping the one with the shortest distance.
    Returns dataframe.
    """
    migrants = migrants.sort_values(by=['edcs_id', 'distance'])
    migrants = migrants.drop_duplicates(subset=['edcs_id'], keep='first')
    print("Removed duplicates.")
    return migrants


def add_details(migrants):
    """
    Adds distance to migrants dataframe and removes duplicates.
    Takes in the migrants database. Where possible, adds distance between origo
    and findspot; removes duplicates, keeping the shortest distance.
    Returns modified dataframe.
    """
    today = datetime.today()
    migrants = remove_nonmigrants(migrants)
    save_database(migrants, today, 'EDCS_Migrants_quick_onlymigrants')
    migrants = round_distances(migrants)
    migrants['distance'] = migrants.apply(lambda row: add_distance(row), axis=1)
    migrants = remove_duplicates(migrants)
    return migrants


def get_master(migrants, edcs):
    """
    Takes in two pandas dataframes containing the migrants and EDCS databases.
    Creates a deep copy of the migrants database: the new master database.
    Loops over the EDCS database. Each entry whose EDCS-ID is not already
    in the master database is added to it.
    Drops the index, sorts by EDCS-ID and returns master database.
    """
    edcs.rename(columns={'edcs-id': 'edcs_id'}, inplace=True)
    master = migrants.copy()
    length_edcs = len(edcs.index)
    counter = 0
    for index, insc in edcs.iterrows():
        if insc['edcs_id'] not in master['edcs_id'].unique():
            master.at[len(master.index)] = insc
            counter += 1
            if counter % 1000 == 0:
                print(f"Added {counter} inscriptions " +
                      f"(ca. {round(100 / length_edcs * counter, 2)}%).")

    master.drop('Index', axis=1, inplace=True)
    master.sort_values(by='edcs-id', inplace=True)
    print("Finished EDCS master database.")
    return master


def quick_master(migrants, edcs):
    edcs.rename(columns={'edcs-id': 'edcs_id'}, inplace=True)
    # master = pd.merge(edcs, migrants, on='edcs_id', how='outer')
    master = pd.merge(edcs, migrants[['edcs_id', 'origo', 'toponym',
                                      'origo_lat', 'origo_long',
                                      'origo_LatLong', 'path', 'pid',
                                      'pleiades', 'located', 'distance']],
                      on='edcs_id', how='left')
    return master


def main():
    """
    Main function. Starts the search for migrants.
    """
    today = datetime.today()

    # edcs = open_database('EDCS_complete_', today)
    # edcs = add_metadata(edcs)
    # save_database(edcs, today, 'EDCS_Metadata')
    edcs = pd.read_csv('EDCS_Metadata_2023-03-14.csv')

    # pleiades_url = 'https://atlantides.org/downloads/pleiades/dumps/' \
    #                'pleiades-names-latest.csv.gz'
    # pleiades = pd.read_csv(pleiades_url, compression='gzip')
    # pleiades = add_coordinates(pleiades)
    # save_database(pleiades, today, 'Pleiades_coordinates')
    # pleiades = get_place_names(pleiades)
    # save_database(pleiades, today, 'Pleiades_placenames')
    # pleiades['stem'] = pleiades.apply(lambda row: add_stem(row), axis=1)
    # save_database(pleiades, today, 'Pleiades_complete')
    # pleiades = pd.read_csv('Pleiades_complete_2023-03-15.csv')

    # migrants = find_migrants(edcs, pleiades)
    # save_database(migrants, today, 'EDCS_Migrants_quick_raw')
    # migrants = pd.read_csv('EDCS_Migrants_quick_raw_2023-03-15.csv')
    # migrants = add_details(migrants)
    # save_database(migrants, today, 'EDCS_Migrants_quick')

    migrants = pd.read_csv('EDCS_Migrants_quick_2023-03-16.csv')
    master = quick_master(migrants, edcs)
    # master = get_master(migrants, edcs)
    save_database(master, today, 'EDCS_Master_quick')


if __name__ == '__main__':
    main()
