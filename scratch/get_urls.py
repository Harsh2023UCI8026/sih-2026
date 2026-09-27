import urllib.request
import urllib.parse
import json
import re

def search(query):
    url = 'https://html.duckduckgo.com/html/?q=' + urllib.parse.quote(query)
    req = urllib.request.Request(
        url, 
        data=None, 
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    )
    try:
        response = urllib.request.urlopen(req)
        html = response.read().decode('utf-8')
        links = re.findall(r'<a class="result__url" href="([^"]+)">([^<]+)</a>', html)
        for link, text in links:
            print(link.replace('//duckduckgo.com/l/?uddg=', ''))
    except Exception as e:
        print(f"Error: {e}")

print("--- June 2024 ---")
search("Yashobhoomi Dwarka Sector-25 June 28 2024 waterlogging site:theweek.in")
print("--- July 2023 ---")
search("Dwarka underpass waterlogging July 2023 site:tribuneindia.com")
search("Dwarka underpass waterlogging July 2023 site:thenewsminute.com")
