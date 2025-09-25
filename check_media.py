#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('wfmu_archive.db')
cur = conn.cursor()

print('Media Status:')
print('=' * 40)
total = cur.execute('SELECT COUNT(*) FROM media').fetchone()[0]
downloaded = cur.execute('SELECT COUNT(*) FROM media WHERE downloaded = 1').fetchone()[0]
not_downloaded = cur.execute('SELECT COUNT(*) FROM media WHERE downloaded = 0').fetchone()[0]

print(f'Total media files: {total}')
print(f'Downloaded: {downloaded}')
print(f'Not downloaded: {not_downloaded}')
print()

print('Media by type:')
for row in cur.execute('SELECT media_type, COUNT(*) FROM media GROUP BY media_type ORDER BY COUNT(*) DESC').fetchall():
    print(f'  {row[0]}: {row[1]}')

print()
print('Sample media URLs:')
for row in cur.execute('SELECT url, media_type FROM media LIMIT 5').fetchall():
    print(f'  {row[1]}: {row[0]}')

conn.close()