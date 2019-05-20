import csv
import gzip
import io
import unicodedata
import urllib.request
import numpy as np

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
	turnout = (table['voters_voted_at_station'] + table['voters_voted_early'] + table['voters_voted_outside_station']).astype(np.float32) / table['voters_registered']
	extra = dict(ballots_valid_invalid = table['ballots_valid'] + table['ballots_invalid'], leader = leader, territory = table['tik_name'], precinct = table['uik_num'], turnout = turnout)

	names = table.dtype.names + tuple(extra.keys())
	return np.rec.fromarrays([table[n] if n in table.dtype.names else extra[n] for n in names], names=names)

def filter(D, region_name=None, region_code = None, voters_registered_min=None, voters_voted_le_voters_registered=False, foreign=None, ballots_valid_invalid_min=None):
	idx = np.full(len(D), True)

	if region_code:
		idx &= D.region_code == region_code

	if region_name:
		idx &= D.region_name == region_name

	if voters_registered_min is not None:
		idx &= D.voters_registered >= voters_registered_min
	
	if ballots_valid_invalid_min is not None:
		idx &= D.ballots_valid_invalid >= ballots_valid_invalid_min

	if voters_voted_le_voters_registered:
		idx &= D.voters_voted <= D.voters_registered

	if foreign is not None:
		idx &= D.foreign == foreign

	return D[idx]
