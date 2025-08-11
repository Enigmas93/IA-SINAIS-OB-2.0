import requests
import json

try:
    response = requests.get('http://localhost:5000/api/config')
    print('Config API Status:', response.status_code)
    
    if response.status_code == 200:
        data = response.json()
        print('Take Profit:', data.get('take_profit', 'NOT FOUND'))
        print('Stop Loss:', data.get('stop_loss', 'NOT FOUND'))
        print('Full response:', json.dumps(data, indent=2))
    else:
        print('Error response:', response.text)
        
except Exception as e:
    print('Error:', str(e))