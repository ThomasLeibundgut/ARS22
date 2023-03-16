# ARS22
Code used in preparation for the ARS22 presentation.
The Code is presented as-is, and will not be updated. The final code used in the dissertation will be made available at a future date. Nevertheless, any comments are welcome.

## Workflow
1. EDCS_S_Scrape.py is used to download all the data in HTML format from the Epigraphik Datenbank Clauss Slaby and save it to a txt file.
2. EDCS_S_Extract.py converts the raw HTML to a more or less neat table, with one line for each inscription, and all information in specific columns.
3. EDCS_Find_Migrants_quick.py, on the basis of the Pleiades Names database, looks for toponyms in the inscription text, thus identifying migrants.
4. EDCS_Analyse_Inscriptions.py provides the analysis of the migrants and draws the graphs.
