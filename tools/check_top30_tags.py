import os, json
enrich_dir = 'data/coin_enrichment'
top30 = ['OPN','CREAM','STO','PNT','WLD','EPIC','EDEN','ENA','AR','SUSHI','KDA','UTK','CLV','XPL','MDX','PHA','NEAR','MEME','ONDO','WAVES','OSMO','ALLO','HAEDAL','ARKM','ZRO','SSV','DODO','ELF','REN','FLM']
ok=0; missing=0; nofile=0
for sym in top30:
    fn = f'{sym}USDT.json'
    path = os.path.join(enrich_dir, fn)
    if os.path.exists(path):
        data = json.load(open(path))
        has_a7 = 'A7' in data.get('tags', {})
        if has_a7:
            ok+=1
        else:
            missing+=1
            print(f'MISS {sym}USDT (exists but no A7 tag)')
    else:
        nofile+=1
        print(f'NOFILE {sym}USDT (no enrich file at all)')
print(f'\nSummary: {ok} tagged, {missing} missing tag, {nofile} no file (total {len(top30)})')
