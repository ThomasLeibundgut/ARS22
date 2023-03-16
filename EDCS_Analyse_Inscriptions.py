import math
from pick import pick
import numpy as np
import pandas as pd
import statistics
import textwrap
from matplotlib import pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import scipy.stats as stats
from scipy.interpolate import InterpolatedUnivariateSpline


def open_database(name, date):
    """
    Opens csv database and returns it as a pandas dataframe.
    Takes in the name of the database and today's date.
    Searches for the most recent version of the database; returns it.
    """
    searching = True
    while searching:
        date_str = date.strftime('%Y-%m-%d')
        filename = f"{name}_{date_str}.csv"
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


def descriptive_statistics(master):
    all_mig = (master['contains_name'] == 1) | (master['contains_name'] == 0)
    funerary = master['funerary'] == 1
    male = master['gender'] == 'm'
    female = master['gender'] == 'f'
    slave = master['legal_status'] == 0
    freed = master['legal_status'] == 1
    free = master['legal_status'] == 2
    groups = {'all': all_mig, 'male': male, 'female': female, 'slave': slave,
              'freed': freed, 'free': free, 'funerary': funerary}
    perc = [.1, .25, .5, .75, .9]

    # overall summary statistics
    print('Summary Statistics for the EDCS:\n')
    for k, v in groups.items():
        print(f'Number of {k}: {len(master[v])}')
    print(f'Number of funerary male: {len(master[funerary & male])}')
    print(f'Number of funerary female: {len(master[funerary & female])}')

    master_fun = master[funerary]

    # Summary statistics for socioeconomic status
    for k, v in groups.items():
        description = master[funerary & v]['text_length'].describe(percentiles=perc)
        print(f'\nSummary SOCIOECONOMIC STATUS statistics for FUNERARY '
              f'{k.capitalize()}: \n{description}')

    # Summary statistics for TRIMMED socioeconomic status
    for k, v in groups.items():
        result = np.array(sorted(master[funerary & v]['text_length'].dropna()))
        trim = int(10 * result.size / 100)
        trimmed = pd.Series(result[trim:-trim])
        print(f'\nTrimmed descriptive SOCIOECONOMIC STATUS statistics for '
              f'{k.capitalize()}: \n{trimmed.describe()}')


def migrant_statistics(migrants):
    all_mig = migrants['funerary'] == 1
    male = migrants['gender'] == 'm'
    female = migrants['gender'] == 'f'
    slave = migrants['legal_status'] == 0
    freed = migrants['legal_status'] == 1
    free = migrants['legal_status'] == 2
    groups = {'all': all_mig, 'male': male, 'female': female,
              'slave': slave, 'freed': freed, 'free': free}
    perc = [.1, .25, .5, .75, .9]

    # summary statistics for distance
    t = stats.ttest_ind(migrants[male]['distance'],
                        migrants[female]['distance'],
                        equal_var=False, nan_policy='omit')
    print(t)
    for k, v in groups.items():
        description = migrants[v]['distance'].describe(percentiles=perc)
        print(f'\nSummary DISTANCE statistics for {k.capitalize()}:\n'
              f'{description}')

    # Trimmed statistics for distance
    for k, v in groups.items():
        result = np.array(sorted(migrants[v]['distance'].dropna()))
        trim = int(10 * result.size / 100)
        trimmed = pd.Series(result[trim:-trim])
        print(f'\nTrimmed descriptive DISTANCE statistics for '
              f'{k.capitalize()}: \n{trimmed.describe()}')

    # Summary statistics for socioeconomic status
    t = stats.ttest_ind(migrants[male]['text_length'],
                        migrants[female]['text_length'],
                        equal_var=False, nan_policy='omit')
    print(t)
    for k, v in groups.items():
        description = migrants[v]['text_length'].describe(percentiles=perc)
        print(f'\nSummary SOCIOECONOMIC STATUS statistics for '
              f'{k.capitalize()}: \n{description}')

    # Trimmed statistics for socioeconomic status
    for k, v in groups.items():
        result = np.array(sorted(migrants[v]['text_length'].dropna()))
        trim = int(10 * result.size / 100)
        trimmed = pd.Series(result[trim:-trim])
        print(f'\nTrimmed descriptive SOCIOECONOMIC STATUS statistics for '
              f'{k.capitalize()}: \n{trimmed.describe()}')

    # most common destinations:
    groups = {'all': all_mig, 'male': male, 'female': female}
    for k, v in groups.items():
        migrants[v]['findspot'].value_counts().reset_index().to_csv(f'Finspot_'
                                                                    f'{k}.csv')
        migrants[v]['province'].value_counts().reset_index().to_csv(f'Province_'
                                                                    f'{k}.csv')
        migrants[v]['origo'].value_counts().reset_index().to_csv(f'Origo_'
                                                                 f'{k}.csv')


def get_stats(edcs):
    men = edcs[edcs['gender'] == 'm']['distance'].dropna()
    women = edcs[edcs['gender'] == 'f']['distance'].dropna()
    print(f'Mann Whitney: {round(stats.mannwhitneyu(men, women)[1], 3)}')
    print(f'T-Test: {round(stats.ttest_ind(men, women)[1], 3)}')
    print(f'Kolmogorow-Smirnow: {round(stats.ks_2samp(men, women)[1], 3)}')


def time_stats(edcs):
    sns.set()
    sns.set_style('white')
    edcs['time'] = (edcs['time_from'] + edcs['time_to']) / 2
    print(edcs['time_from'].value_counts())
    edcs = edcs.sort_values(by=['gender'], ascending=True)
    fig, ax = plt.subplots()
    sns.histplot(data=edcs, x='time_from', binwidth=25, hue='gender', hue_order=['m', 'f'], ax=ax)
    ax.set(xlabel='Time (lower bound)', title='Temporal Distribution of Migrants')
    ax.legend(loc='upper right', labels=['female', 'male'])
    plt.show()


def overall_plots(edcs):
    sns.set()
    sns.set_style('white')
    edcs = edcs.sort_values(by=['gender'], ascending=True)

    fig, ax = plt.subplots()
    sns.kdeplot(data=edcs[edcs['gender'] == 'm']['distance'], ax=ax)
    sns.kdeplot(data=edcs[edcs['gender'] == 'f']['distance'], ax=ax)
    ax.set(xlabel='Distance (km)', ylabel='Density', title='Distance Migrated')
    ax.legend(loc='upper right')
    plt.legend(labels=['male', 'female'])
    plt.show()

    fig, ax = plt.subplots()
    sns.histplot(data=edcs, x='distance', binwidth=100, hue='gender', hue_order=['m', 'f'], ax=ax)
    ax.set(xlabel='Distance (km)', title='Distance Migrated')
    ax.legend(loc='upper right', labels=['female', 'male'])
    plt.show()


def set_province(row):
    italy = ['Latium et Campania / Regio I', 'Apulia et Calabria / Regio II',
             'Bruttium et Lucania / Regio III', 'Samnium / Regio IV',
             'Picenum / Regio V', 'Umbria / Regio VI', 'Etruria / Regio VII',
             'Aemilia / Regio VIII', 'Liguria / Regio IX',
             'Venetia et Histria / Regio X', 'Transpadana / Regio XI']
    if row['province'] in italy:
        return 'Italia'
    return row['province']


def italia(edcs):
    edcs['province'] = edcs['province'].str.strip()
    edcs['province'].mask(edcs['province'] == "Belgica | Germania inferior",
                          "Belgica", inplace=True)
    edcs['province'].mask(edcs['province'] == "Belgica | Germania superior",
                          "Belgica", inplace=True)
    edcs['province'].mask(edcs['province'] == "Aquitani(c)a",
                          "Aquitania", inplace=True)
    edcs['province'].mask(edcs['province'] == "Aquitani",
                          "Aquitania", inplace=True)
    edcs['province'] = edcs.apply(lambda row: set_province(row), axis=1)

    edcs = edcs.sort_values(by=['gender'], ascending=True)
    return edcs


def provinces_plots(edcs):
    sns.set()
    sns.set_style('white')

    provs = ['Italia', 'Roma', 'Lusitania', 'Africa proconsularis', 'Baetica']
    m = edcs['gender'] == 'm'
    f = edcs['gender'] == 'f'

    for prov in provs:
        # provinces kde plots
        p = edcs['province'] == prov
        fig, ax = plt.subplots()
        sns.kdeplot(data=edcs[p & m]['distance'], ax=ax)
        sns.kdeplot(data=edcs[p & f]['distance'], ax=ax)
        men = len(edcs[p & m])
        women = len(edcs[p & f])
        ax.set(xlabel='Distance (km)', ylabel='Density',
               title=f'{prov}: Distance Migrated')
        ax.legend(loc='upper right')
        plt.legend(labels=[f'male (n={men})', f'female (n={women})'])
        plt.show()
        # plt.savefig(f'KDE_{prov}.png')
        # plt.close()

        # provinces histograms
        fig, ax = plt.subplots()
        sns.histplot(data=edcs[p], x='distance', binwidth=100, hue='gender', hue_order=['m', 'f'], ax=ax)
        ax.set(xlabel='Distance (km)', title=f'{prov}: Distance Migrated')
        ax.legend(loc='upper right', labels=[f'female (n={women})', f'male (n={men})'])
        plt.show()
        # plt.savefig(f'HIST_{prov}.png')
        # plt.close()


def get_stats_prov(edcs):
    m = edcs['gender'] == 'm'
    f = edcs['gender'] == 'f'
    provs = ['Italia', 'Roma', 'Lusitania', 'Africa proconsularis', 'Baetica']

    for prov in provs:
        p = edcs['province'] == prov
        men = edcs[m & p]['distance'].dropna()
        women = edcs[f & p]['distance'].dropna()
        print(f'\n{prov.capitalize()}:')
        print(f'Mann Whitney: {round(stats.mannwhitneyu(men, women)[1], 3)}')
        print(f'T-Test: {round(stats.ttest_ind(men, women)[1], 3)}')
        print(f'Kolmogorow-Smirnow: {round(stats.ks_2samp(men, women)[1], 3)}')


def province_statistics(edcs):
    m = edcs['gender'] == 'm'
    f = edcs['gender'] == 'f'
    i = edcs['legal_status'] == 2
    l = edcs['legal_status'] == 1
    s = edcs['legal_status'] == 0

    provs = ['Italia', 'Roma', 'Lusitania', 'Africa proconsularis', 'Baetica']
    provs = ['Lusitania', 'Africa proconsularis']

    for prov in provs:
        p = edcs['province'] == prov
        tot = edcs[p]['distance']
        men = edcs[m & p]['distance']
        women = edcs[f & p]['distance']
        m_eco = np.array(sorted(edcs[p & m]['text_length'].dropna()))
        f_eco = np.array(sorted(edcs[p & f]['text_length'].dropna()))
        a_eco = np.array(sorted(edcs[p ]['text_length'].dropna()))
        ingenui = len(edcs[p & i])
        liberti = len(edcs[p & l])
        servi = len(edcs[p & s])
        m_i = len(edcs[p & m & i])
        m_l = len(edcs[p & m & l])
        m_s = len(edcs[p & m & s])
        f_i = len(edcs[p & f & i])
        f_l = len(edcs[p & f & l])
        f_s = len(edcs[p & f & s])

        print(f'\n{prov.capitalize()}: categories alle:')
        print(f'ingenui: {ingenui}; liberti: {liberti}; servi: {servi}.')
        print(f'\n{prov.capitalize()}: categories Männer:')
        print(f'ingenui: {m_i}; liberti: {m_l}; servi: {m_s}.')
        print(f'\n{prov.capitalize()}: categories Frauen:')
        print(f'ingenui: {f_i}; liberti: {f_l}; servi: {f_s}.')
        input('continue? ')

        trim_tot = int(10 * tot.size / 100)
        trimmed_tot = pd.Series(tot[trim_tot:-trim_tot])

        trim_men = int(10 * men.size / 100)
        trimmed_men = pd.Series(men[trim_men:-trim_men])

        trim_women = int(10 * women.size / 100)
        trimmed_women = pd.Series(women[trim_women:-trim_women])

        print(f'\n{prov.capitalize()}: Trimmed distance statistics for:')
        print(f'Alle:\n{trimmed_tot.describe()}\n'
              f'\nMen:\n{trimmed_men.describe()}\n'
              f'\nWomen:\n{trimmed_women.describe()}\n')
        input('continue? ')

        trim_tot = int(10 * a_eco.size / 100)
        trimmed_tot = pd.Series(a_eco[trim_tot:-trim_tot])

        trim_men = int(10 * m_eco.size / 100)
        trimmed_men = pd.Series(m_eco[trim_men:-trim_men])

        trim_women = int(10 * f_eco.size / 100)
        trimmed_women = pd.Series(f_eco[trim_women:-trim_women])

        print(f'\n{prov.capitalize()}:\nTrimmed socio-econ statistics for:')
        print(f'Alle:\n{trimmed_tot.describe()}\n'
              f'\nMen:\n{trimmed_men.describe()}\n'
              f'\nWomen:\n{trimmed_women.describe()}\n')
        input('continue? ')


def analyse_inscriptions(today):
    migrants = open_database('EDCS_Migrants_quick', today)
    # master = open_database('EDCS_Master_quick', today)
    # descriptive_statistics(master)
    # migrant_statistics(migrants)
    # get_stats(migrants)
    # time_stats(migrants)
    # overall_plots(migrants)
    # migrants = italia(migrants)
    # migrants = provinces_plots(migrants)
    # get_stats_prov(migrants)
    province_statistics(migrants)


def main():
    """
    Main function. Starts the search for migrants.
    """
    today = datetime.today()

    analyse_inscriptions(today)


if __name__ == "__main__":
    main()
