import requests, json
base = 'http://127.0.0.1:8000'
# Approve non-existent post
r = requests.post(f'{base}/api/aprovar/9999', json={})
print('Approve non-existent:', r.status_code, r.text)
# Set invalid schedule times
r = requests.post(f'{base}/api/horarios', json={'hora_manha':'25:00','hora_noite':'13:00'})
print('Set invalid schedule:', r.status_code, r.text)
# Get status
r = requests.get(f'{base}/api/status')
print('Status endpoint:', r.status_code, r.text)
