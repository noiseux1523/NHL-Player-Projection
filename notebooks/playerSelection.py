from __future__ import print_function
import pickle
import os.path
import datetime
import time
import pandas as pd
import numpy as np
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from pulp import *


def get_values(SAMPLE_SPREADSHEET_ID, SAMPLE_RANGE_NAME):
    """Shows basic usage of the Sheets API.
    Prints values from a sample spreadsheet.
    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('sheets', 'v4', credentials=creds)

    # Call the Sheets API
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                range=SAMPLE_RANGE_NAME).execute()
    values = result.get('values', [])

    if not values:
        print('No data found.')
    
    return values


def get_selection(nhl):
    # Setup
    nhl_unpicked = nhl[nhl.status != 'o']
    player = [str(i) for i in range(nhl_unpicked.shape[0])]
    point = {str(i): int(nhl_unpicked['proj'].iloc[i]) for i in range(nhl_unpicked.shape[0])} 
    cost = {str(i): int(nhl_unpicked['cap_hit'].iloc[i]) for i in range(nhl_unpicked.shape[0])}
    end = {str(i): int(nhl_unpicked['end'].iloc[i]) for i in range(nhl_unpicked.shape[0])} 
    att = {str(i): 1 if nhl_unpicked['pos'].iloc[i] == 'A' else 0 for i in range(nhl_unpicked.shape[0])}
    defe = {str(i): 1 if nhl_unpicked['pos'].iloc[i] == 'D' else 0 for i in range(nhl_unpicked.shape[0])}
    goal = {str(i): 1 if nhl_unpicked['pos'].iloc[i] == 'G' else 0 for i in range(nhl_unpicked.shape[0])}
    xi = {str(i): 1 for i in range(nhl_unpicked.shape[0])}
    prob = LpProblem("Fantasy Hockey", LpMaximize)
    player_vars = LpVariable.dicts("Players", player, cat=LpBinary)
    
    # Objective function
    prob += lpSum([point[i] * player_vars[i] for i in player]), "Total Cost"
    
    # Constraints
    spots_to_fill = 22 - nhl[nhl.status == 'o'].shape[0]
    nb_forwards = nhl[(nhl.status == 'o') & (nhl['pos']=='A')].shape[0]
    nb_def = nhl[(nhl.status == 'o') & (nhl['pos']=='D')].shape[0]
    nb_goalers = nhl[(nhl.status == 'o') & (nhl['pos']=='G')].shape[0]
    money_left = nhl[nhl.status == 'o']['cap_hit'].sum()
    
    prob += lpSum([player_vars[i] for i in player]) == spots_to_fill, "Total {spots_to_fill} Players"
    prob += lpSum([cost[i] * player_vars[i] for i in player]) <= 81500000 - money_left, "Total Cost"
    prob += lpSum([att[i] * player_vars[i] for i in player]) <= 13-nb_forwards, "Less than 13 att"
    prob += lpSum([defe[i] * player_vars[i] for i in player]) <= 7-nb_def, "Less than 7 def"
    prob += lpSum([goal[i] * player_vars[i] for i in player]) <= 2-nb_goalers, "Less than 2 goalers"
    
    # Solve
    status = prob.solve()
    
    # Selection
    selection = {}
    for v in prob.variables():
        index = int(v.name.split("_")[1])
        selection[index] = v.varValue
    nhl_unpicked['label'] = 0.0
    nhl_unpicked = nhl_unpicked.reset_index()
    for i in selection:
        nhl_unpicked.loc[i, 'label'] = selection[i]
        
    # Display
    XI = nhl_unpicked[nhl_unpicked['label'] == 1.0]
    TOTAL_POINTS = XI['proj'].sum() + nhl[(nhl.status == 'o') & (nhl['pos']=='A')]['proj'].sum()\
                                    + nhl[(nhl.status == 'o') & (nhl['pos']=='D')]['proj'].sum()\
                                    + nhl[(nhl.status == 'o') & (nhl['pos']=='G')]['proj'].sum()
    curren_cost = + nhl[(nhl.status == 'o') & (nhl['pos']=='A')]['cap_hit'].sum()\
                  + nhl[(nhl.status == 'o') & (nhl['pos']=='D')]['cap_hit'].sum()\
                  + nhl[(nhl.status == 'o') & (nhl['pos']=='G')]['cap_hit'].sum()
    TOTAL_COST = XI['cap_hit'].sum() + curren_cost
    TOTAL_PLAYERS = XI.shape[0] + nhl[(nhl.status == 'o') & (nhl['pos']=='A')].shape[0]\
                                + nhl[(nhl.status == 'o') & (nhl['pos']=='D')].shape[0]\
                                + nhl[(nhl.status == 'o') & (nhl['pos']=='G')].shape[0]
    
    # TODO: Modify with current cap hit
    if TOTAL_COST > 81500000:
        raise Exception(f'Current cap hit: {TOTAL_COST}, Total cap should not exceed 81,500,000')
    '''
    TODO: Print current players, and players to add
    '''
    os.system('cls' if os.name == 'nt' else 'clear')
    print("Projected Points: {:,}\nCost: {:,}\nPlayers: {}\nCurrent Roster: {}".format(TOTAL_POINTS, TOTAL_COST, TOTAL_PLAYERS, nhl[nhl.status == 'o'].shape[0]))
    print("Cap Used: {:,}\nCap per Player Left: {:,}\n".format(curren_cost, int((81500000-curren_cost)/(22-nhl[nhl.status == 'o'].shape[0]))))
    print('FORWARDS')
    print('---------------------------------------------')
    print('CURRENT')
    if nhl[(nhl.status == 'o') & (nhl['pos']=='A')].shape[0] >0:
        print(nhl[nhl.status == 'o'][['name','pos','proj','cap_hit', 'end']][nhl[nhl.status == 'o']['pos']=='A'].sort_values(['pos']).reset_index(drop=True))
    print('---------------------------------------------')
    print('SUGGESTED')
    print(XI[['name','pos','proj','cap_hit', 'end']][XI['pos']=='A'].sort_values(['pos']).reset_index(drop=True))
    print('\nDEFENSEMEN')
    print('---------------------------------------------')
    print('CURRENT')
    if nhl[(nhl.status == 'o') & (nhl['pos']=='D')].shape[0] >0:
        print(nhl[nhl.status == 'o'][['name','pos','proj','cap_hit', 'end']][nhl[nhl.status == 'o']['pos']=='D'].sort_values(['pos']).reset_index(drop=True))
    print('---------------------------------------------')
    print('SUGGESTED')
    print(XI[['name','pos','proj','cap_hit', 'end']][XI['pos']=='D'].sort_values(['pos']).reset_index(drop=True))
    print('\nGOALIES')
    print('---------------------------------------------')
    print('CURRENT')
    if nhl[(nhl.status == 'o') & (nhl['pos']=='G')].shape[0] >0:
        print(nhl[nhl.status == 'o'][['name','pos','proj','cap_hit', 'end']][nhl[nhl.status == 'o']['pos']=='G'].sort_values(['pos']).reset_index(drop=True))
    print('---------------------------------------------')
    print('SUGGESTED')
    print(XI[['name','pos','proj','cap_hit', 'end']][XI['pos']=='G'].sort_values(['pos']).reset_index(drop=True))
    print('---------------------------------------------\n')

    return nhl, XI


def main():
    """
    TODO: Make sure the sheet ID in get_values() is correct with the updated stats in the spreadsheet.
    """
    # Read attaquants
    attaquants = get_values('14_yHHExaNXEjFIVRr_OBLtpiWPRjOS-e9TEca6N28xU', 'Attaquants')
    attaquants = pd.DataFrame(attaquants[2:])
    attaquants = attaquants.dropna(subset=[0,36]) # Drop if no name or nan cap hits
    attaquants = attaquants[attaquants[36]!='']
    attaquants['pos'] = 'A'

    # Read defenseurs
    defenseurs = get_values('14_yHHExaNXEjFIVRr_OBLtpiWPRjOS-e9TEca6N28xU', 'Defenseurs')
    defenseurs = pd.DataFrame(defenseurs[2:])
    defenseurs = defenseurs.dropna(subset=[0,36]) # Drop if no name or nan cap hits
    defenseurs = defenseurs[defenseurs[36]!='']
    defenseurs['pos'] = 'D'

    # Read gardiens
    gardiens = get_values('14_yHHExaNXEjFIVRr_OBLtpiWPRjOS-e9TEca6N28xU', 'Gardiens')
    gardiens = pd.DataFrame(gardiens[1:])
    gardiens = gardiens.dropna(subset=[0,21]) # Drop if no name or nan cap hits
    gardiens['pos'] = 'G'
    
    # Preprocessing
    nhl = pd.concat([attaquants[[4,5,'pos',13,36,37]].rename({4: 'name', 5: 'status', 13: 'proj', 36: 'cap_hit', 37: 'end'}, axis=1), 
                     defenseurs[[4,5,'pos',13,36,37]].rename({4: 'name', 5: 'status', 13: 'proj', 36: 'cap_hit', 37: 'end'}, axis=1), 
                     gardiens[[1,2,'pos',12,21,22]].rename({1: 'name', 2: 'status', 12: 'proj', 21: 'cap_hit', 22: 'end'}, axis=1)],
                     ignore_index=True)
    nhl['cap_hit'] = nhl['cap_hit'].replace(',', '', regex=True).astype(int)
    nhl['proj'] = nhl['proj'].astype(int)
    nhl = nhl[nhl.status != 'x'] # Only look at available players
    nhl = nhl[nhl.proj > 0] # Only keep players with more than 0 projected points
    
    # Knapsack 1st tier
    nhl_selection1, X1 = get_selection(nhl)

    return X1
        
if __name__ == '__main__':
    while True:
        print(datetime.datetime.now())
        nhl_selection1 = main()
        time.sleep(15)
        
