import asyncio
import aiohttp
from bs4 import BeautifulSoup

async def test_scrape():
    url = 'https://blog.wfmu.org/'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            print(f"Status: {response.status}")
            if response.status == 200:
                html = await response.text()
                print(f"HTML Length: {len(html)}")

                soup = BeautifulSoup(html, 'lxml')

                # Check for post titles
                titles = soup.find_all('h3', class_='title')
                print(f"Found {len(titles)} post titles")
                for title in titles[:3]:
                    link = title.find('a')
                    if link:
                        print(f"  - {link.get_text(strip=True)}")

                # Check for categories
                cat_list = soup.find('ul', id='categories')
                if cat_list:
                    cats = cat_list.find_all('a')
                    print(f"Found {len(cats)} categories")
                else:
                    print("Categories list not found")

                # Check for navigation
                older = soup.find('a', string='Older Posts')
                if older:
                    print(f"Next page: {older.get('href')}")
                else:
                    print("No 'Older Posts' link found")

                # Debug: print some of the HTML structure
                print("\n--- HTML Preview ---")
                print(html[:2000])

asyncio.run(test_scrape())