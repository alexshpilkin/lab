import csv
import gzip
import io
import re
import unicodedata
import urllib.request
import numpy as np

# https://www.iana.org/assignments/media-types/text/tab-separated-values
class ietf_tab(csv.Dialect):
	delimiter = '\t'
	lineterminator = '\n'  # use universal newlines
	quoting = csv.QUOTE_NONE
csv.register_dialect('ietf-tab', ietf_tab)

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

def urlopen(fileorurl):
  if isinstance(fileorurl, io.BufferedIOBase):
    return io.BufferedReader(fileorurl)
  elif re.fullmatch(r'[A-Za-z0-9.+-]+://.*', fileorurl):  # RFC 3986
    return urllib.request.urlopen(fileorurl)
  else:
    return open(fileorurl, 'rb')

def loadnpz(fileorurl, year):
  with urlopen(fileorurl) as file:
    table = np.load(io.BytesIO(file.read()))['_' + str(year)]
  return load(table)

def loadtsv(fileorurl):
  with urlopen(fileorurl) as file:
    if file.peek(1)[:1] == b'\x1f':  # gzip magic
      file = gzip.GzipFile(fileobj=file)
    rd = csv.DictReader(io.TextIOWrapper(file, newline='\r\n'), dialect='ietf-tab')
    it = iter(rd)
    first = next(it)

    types = []
    for name, value in zip(rd.fieldnames, first.values()):
      if value.isdigit():
        type = '<i4'
      elif value.replace('.', '', 1).isdigit():
        type = '<f8'
      else:
        type = '<U127'
      types.append((toident(name), type))

    table = np.array([tuple(first.values())], dtype=types)
    i = 1
    for row in it:
      if i >= len(table):
        table.resize(2*len(table))
      table[i] = tuple(row.values())
      i += 1
    table.resize(i)

    return load(table)

def load(table):
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
  territory = np.chararray.replace(table['tik'], 'Территориальная избирательная комиссия', 'ТИК')
  precinct  = table['uik']
  return np.rec.fromarrays([leader, voters_registered, voters_voted, ballots_valid_invalid, region, territory, precinct], names=COLUMNS)
