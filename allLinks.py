from bs4 import BeautifulSoup
import requests

url = "https://www.ellindecoratie.nl/" 
headers = {'User-Agent': 'Mozilla/5.0'}
response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.text, 'html.parser')

# print(soup)
print(response.status_code)  

links = soup.find_all('a')
for link in links:
    print(link.get('href'))