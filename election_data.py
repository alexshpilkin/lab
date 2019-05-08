#import json
import io
import re
import unicodedata
import urllib.request
import numpy as np

TRANSLIT = ('АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ'
            'абвгдеёжзийклмнопрстуфхцчшщъыьэюя',
            'ABVGDEËŽZIJKLMNOPRSTUFHCČŠŜ"Y\'ÈÛÂ'
            'abvgdeëžzijklmnoprstufhcčšŝ"y\'èûâ')  # ISO 9:1995
TRANSLIT = {ord(a): ord(b) for a, b in zip(*TRANSLIT)}
COLUMNS = ('leader', 'voters_registered', 'voters_voted', 'ballots_valid_invalid', 'region', 'territory', 'precinct')

def translit(s):
  return s.translate(TRANSLIT)

def toident(s):
  s = unicodedata.normalize('NFD', translit(s)).encode('ascii', 'ignore').decode('ascii')
  return (s.lower().replace(' ', '_').replace(',', '').replace('.', '')
           .replace('"', '').replace("'", '').replace('(', '').replace(')', ''))

def urlopen(url):
  if re.fullmatch(r'[A-Za-z0-9.+-]+://.*', url):  # RFC 3986
    return urllib.request.urlopen(url)
  else:
    return open(url, 'rb')

def loadnpz(url, year):
  with urlopen(url) as file:
    table = np.load(io.BytesIO(file.read()))['_' + str(year)]

  def flt(include, exclude=()):
    return [col
            for col in table.dtype.names
            if any(toident(f) in col for f in include) and
               all(toident(f) not in col for f in exclude)]

  leader = np.squeeze(table[flt({'Путин', 'Единая Россия', 'Медведев'})[0]])
  voters_registered = np.squeeze(table[flt({'Число избирателей, включенных', 'Число избирателей, внесенных'})[0]])
  voters_voted = np.sum(np.vstack([table[c] for c in flt({'бюллетеней, выданных'})]).T, axis=1)
  ballots_valid_invalid = np.sum(np.vstack([table[c] for c in flt({'действительных', 'недействительных'}, {'отметок'})]).T, axis=1)
  region    = table['region']
  territory = table['tik']
  precinct  = table['uik']
  return np.rec.fromarrays([leader, voters_registered, voters_voted, ballots_valid_invalid, region, territory, precinct], names=COLUMNS)
