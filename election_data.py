import csv
import gzip
import io
import unicodedata
import urllib.request
import numpy as np


COLUMNS = ('leader', 'region_code', 'voters_registered', 'voters_voted', 'ballots_valid_invalid', 'region', 'territory', 'precinct', 'foreign')

TRANSLIT = ('АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ'
            'абвгдеёжзийклмнопрстуфхцчшщъыьэюя',
            'ABVGDEËŽZIJKLMNOPRSTUFHCČŠŜ"Y\'ÈÛÂ'
            'abvgdeëžzijklmnoprstufhcčšŝ"y\'èûâ') # ISO 9:1995
TRANSLIT = {ord(a): ord(b) for a, b in zip(*TRANSLIT)}

def translit(s):
	return s.translate(TRANSLIT)

def toident(s):
	s = unicodedata.normalize('NFD', translit(s)).encode('ascii', 'ignore').decode('ascii')
	return s.lower().replace(' ', '_').translate({ord(c) : None for c in ''',."'()'''})

def load(fileorurl):
	file = ((urllib.request.urlopen(fileorurl)
	         if fileorurl.startswith('http')
	         else open(fileorurl, 'rb'))
	        if isinstance(fileorurl, str)
	        else io.BufferedReader(fileorurl))
	with file:
		if file.peek(2).startswith(b'\x1f\x8b'):
			file = gzip.GzipFile(fileobj=file)
		if file.peek(4).startswith(b'PK\x03\x04'):
			table = np.load(io.BytesIO(file.read()))['arr_0']
		elif file.peek(6).startswith(b'\x93NUMPY'):
			table = np.load(io.BytesIO(file.read()))
		else:
			# https://www.iana.org/assignments/media-types/text/tab-separated-values
			rd = csv.DictReader(io.TextIOWrapper(file, newline='\r\n'),
			                    delimiter='\t',
			                    lineterminator='\n',
			                    quoting=csv.QUOTE_NONE)
			it = iter(rd)
			first = next(it)
			dtype = [(toident(name), '<i4' if value.isdigit() else '<f8' if value.replace('.', '', 1).isdigit() or value == 'nan' else '<U512') for name, value in zip(rd.fieldnames, first.values())]
			table = np.array([tuple(first.values())], dtype=dtype)
			for i, row in enumerate(it, start=1):
				if i >= len(table):
					table.resize(2*len(table))
				table[i] = tuple(row.values())
			table.resize(i)
		
	leader = table[[n for n in table.dtype.names if 'putin' in n or 'medvedev' in n][0]]
	territory = np.chararray.replace(table['tik_name'], 'Территориальная избирательная комиссия', 'ТИК')

	columns = list(COLUMNS)
	arrays  = [leader, table['region_code'], table['voters_registered'], table['voters_voted'], table['ballots_valid'] + table['ballots_invalid'], table['region_name'], territory, table['uik_num'], table['foreign']]
	for name in table.dtype.fields:
		if not name.startswith('turnout_'): continue
		columns.append(name)
		arrays.append(table[name])
	return np.rec.fromarrays(arrays, names=columns)

def filter(D, region=None, region_code = None, voters_registered_min=None, voters_voted_le_voters_registered=False, foreign=None, ballots_valid_invalid_min=None):
	idx = np.full(len(D), True)

	if region_code:
		idx &= D.region_code == region_code

	if region:
		idx &= D.region == region

	if voters_registered_min is not None:
		idx &= D.voters_registered >= voters_registered_min
	
	if ballots_valid_invalid_min is not None:
		idx &= D.ballots_valid_invalid >= ballots_valid_invalid_min

	if voters_voted_le_voters_registered:
		idx &= D.voters_voted <= D.voters_registered

	if foreign is not None:
		idx &= D.foreign == foreign

	return D[idx]
