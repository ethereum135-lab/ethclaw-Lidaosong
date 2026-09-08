import os, json

enrich_dir = 'data/coin_enrichment'
targets = ['STRAXUSDT','HMSTRUSDT','PNTUSDT','STGUSDT','KDAUSDT','ELFUSDT','WLFIUSDT','HIFIUSDT','ERNUSDT']
for t in targets:
    path = os.path.join(enrich_dir, t + '.json')
    if os.path.exists(path):
        data = json.load(open(path))
        has_a7 = 'A7' in data.get('tags', {})
        status = 'OK' if has_a7 else 'NO_A7'
        print(f'{t}: {status}')
    else:
        print(f'{t}: NO_FILE')
