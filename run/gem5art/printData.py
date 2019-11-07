from gem5art import run
import json
data = {}
data['vm'] = []
for i in run.getRuns():
    data['vm'].append(i)

with open('data.json', 'w') as outfile:
    json.dump(data, outfile)
