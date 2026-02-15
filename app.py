from flask import Flask, render_template, request, jsonify, send_file
import json
import csv
from collections import Counter
import io

app = Flask(__name__)

def parse_file(file):
    """Parse either JSON or CSV file and return list of teams"""
    filename = file.filename.lower()
    
    if filename.endswith('.json'):
        return json.load(file)
    elif filename.endswith('.csv'):
        # Parse CSV file
        content = file.read().decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(content))
        teams = []
        
        for row in csv_reader:
            # Build players list from CSV columns
            players = []
            for i in range(1, 12):  # 11 players
                player_id = row.get(f'P{i}_ID')
                if player_id:
                    players.append({
                        'position': int(row.get(f'P{i}_Pos', i)),
                        'player_id': int(player_id),
                        'player_name': row.get(f'P{i}_Name', 'Unknown'),
                        'web_name': row.get(f'P{i}_WebName', 'Unknown'),
                        'element_type': int(row.get(f'P{i}_Type', 0)),
                        'is_captain': row.get(f'P{i}_Captain', '').lower() == 'true',
                        'is_vice_captain': row.get(f'P{i}_Vice', '').lower() == 'true',
                        'multiplier': int(row.get(f'P{i}_Multiplier', 1))
                    })
            
            teams.append({
                'rank': int(row.get('Rank', 0)),
                'last_rank': int(row.get('Last_Rank', 0)),
                'team_name': row.get('Team_Name', ''),
                'manager_name': row.get('Manager_Name', ''),
                'entry_id': int(row.get('Entry_ID', 0)),
                'total_points': int(row.get('Total_Points', 0)),
                'event_points': int(row.get('Event_Points', 0)),
                'players': players
            })
        
        return teams
    else:
        raise ValueError('Unsupported file format. Please upload JSON or CSV files.')

@app.route('/')
def index():
    return render_template('index_new.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        # Get uploaded files
        if 'gw1_file' not in request.files or 'gw2_file' not in request.files:
            return jsonify({'error': 'Please upload both gameweek files'}), 400
        
        gw1_file = request.files['gw1_file']
        gw2_file = request.files['gw2_file']
        
        # Parse files (supports both JSON and CSV)
        gw1_data = parse_file(gw1_file)
        gw2_data = parse_file(gw2_file)
        
        # Create Entry ID lookups
        gw1_lookup = {team['entry_id']: team for team in gw1_data}
        gw2_lookup = {team['entry_id']: team for team in gw2_data}
        
        # Find matching teams
        gw1_entry_ids = set(gw1_lookup.keys())
        gw2_entry_ids = set(gw2_lookup.keys())
        matching_entry_ids = gw1_entry_ids & gw2_entry_ids
        
        if len(matching_entry_ids) == 0:
            return jsonify({'error': 'No matching teams found between the two gameweeks'}), 400
        
        # Analyze transfers
        transfers_out_gw1 = []
        transfers_in_gw2 = []
        team_transfer_details = []
        
        for entry_id in matching_entry_ids:
            gw1_team = gw1_lookup[entry_id]
            gw2_team = gw2_lookup[entry_id]
            
            # Get player IDs
            gw1_player_ids = {player['player_id'] for player in gw1_team['players']}
            gw2_player_ids = {player['player_id'] for player in gw2_team['players']}
            
            # Find differences
            players_out = gw1_player_ids - gw2_player_ids
            players_in = gw2_player_ids - gw1_player_ids
            
            if players_out or players_in:
                # Get player details for transfers out
                for player in gw1_team['players']:
                    if player['player_id'] in players_out:
                        transfers_out_gw1.append({
                            'player_id': player['player_id'],
                            'player_name': player['player_name'],
                            'web_name': player['web_name']
                        })
                
                # Get player details for transfers in
                for player in gw2_team['players']:
                    if player['player_id'] in players_in:
                        transfers_in_gw2.append({
                            'player_id': player['player_id'],
                            'player_name': player['player_name'],
                            'web_name': player['web_name']
                        })
                
                team_transfer_details.append({
                    'entry_id': entry_id,
                    'team_name': gw2_team['team_name'],
                    'manager_name': gw2_team['manager_name'],
                    'transfers_out': len(players_out),
                    'transfers_in': len(players_in)
                })
        
        # Count frequencies
        transfers_out_counter = Counter([p['player_id'] for p in transfers_out_gw1])
        transfers_in_counter = Counter([p['player_id'] for p in transfers_in_gw2])
        
        # Create player name mapping
        player_names = {}
        for p in transfers_out_gw1 + transfers_in_gw2:
            if p['player_id'] not in player_names:
                player_names[p['player_id']] = {
                    'player_name': p['player_name'],
                    'web_name': p['web_name']
                }
        
        # Prepare results
        transfers_out_list = []
        for player_id, count in transfers_out_counter.most_common(50):
            player_info = player_names[player_id]
            transfers_out_list.append({
                'player_id': player_id,
                'player_name': player_info['player_name'],
                'web_name': player_info['web_name'],
                'count': count
            })
        
        transfers_in_list = []
        for player_id, count in transfers_in_counter.most_common(50):
            player_info = player_names[player_id]
            transfers_in_list.append({
                'player_id': player_id,
                'player_name': player_info['player_name'],
                'web_name': player_info['web_name'],
                'count': count
            })
        
        # Return results
        return jsonify({
            'success': True,
            'summary': {
                'teams_analyzed': len(matching_entry_ids),
                'teams_with_transfers': len(team_transfer_details),
                'total_transfers_out': len(transfers_out_gw1),
                'total_transfers_in': len(transfers_in_gw2),
                'unique_players_out': len(transfers_out_counter),
                'unique_players_in': len(transfers_in_counter)
            },
            'transfers_out': transfers_out_list,
            'transfers_in': transfers_in_list,
            'team_transfers': sorted(team_transfer_details, 
                                    key=lambda x: x['transfers_out'] + x['transfers_in'], 
                                    reverse=True)[:100]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
