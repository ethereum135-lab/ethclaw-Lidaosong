import sys,xml.etree.ElementTree as ET
data=sys.stdin.read()
if not data.strip():
    print('NO DATA')
    sys.exit(0)
try:
    root=ET.fromstring(data)
    items=root.findall('.//item')[:5]
    for item in items:
        title=item.find('title')
        link=item.find('link')
        pubDate=item.find('pubDate')
        print(f'- {title.text if title is not None else "N/A"}')
        print(f'  Link: {link.text if link is not None else "N/A"}')
        print(f'  Time: {pubDate.text if pubDate is not None else "N/A"}')
        print()
except Exception as e:
    print(f'Parse error: {e}')
