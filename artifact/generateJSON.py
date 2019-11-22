import json
from uuid import UUID
from pymongo import MongoClient
data = {}
def _convertForJson(d):
    for k,v in d.items():
        if isinstance(v, UUID):
            d[k] = str(v)
        if isinstance(v, list):
            v = [str(s) for s in v]
            d[k] = v
    return d
db = MongoClient().artifact_database
data['gem5Data'] = []
for i in db.artifacts.find(limit=20):
    data['gem5Data'].append(_convertForJson(i))

with open('data.json', 'w') as outfile:
    json.dump(data['gem5Data'],outfile)
