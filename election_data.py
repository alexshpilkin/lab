import re
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
			#head = np.genfromtxt(io.BytesIO(b), max_rows = 2 if has_names else 1, delimiter = delimiter, names = True if has_names else None, dtype = None, encoding = encoding)
			rd = csv.reader(io.TextIOWrapper(file), delimiter = '\t', lineterminator='\n')
			it = iter(rd)
			fieldnames = next(it)
			first = next(it)
			dtype = [(name, '<i4' if value.isdigit() else '<f8' if value.replace('.', '', 1).isdigit() or value == 'nan' else '<U512') for name, value in zip(fieldnames, first)]
			table = np.array([tuple(first)], dtype=dtype)
			for i, row in enumerate(it, start=1):
				if i >= len(table):
					table.resize(2 * len(table))
				table[i] = tuple(int(v) if dtype[j][1][1] == 'i' else float(v) if dtype[j][1][1] == 'f' else v for j, v in enumerate(row))
			table.resize(i)
		
	leader = table[[n for n in table.dtype.names if 'putin' in n or 'medvedev' in n][0]]
	turnout = (table['voters_voted_at_station'] + table['voters_voted_early'] + table['voters_voted_outside_station']).astype(np.float32) / table['voters_registered']
	extra = dict(ballots_valid_invalid = table['ballots_valid'] + table['ballots_invalid'], leader = leader, territory = table['tik_name'], precinct = table['uik_num'], turnout = turnout)

	names = table.dtype.names + tuple(extra.keys())
	return np.rec.fromarrays([table[n] if n in table.dtype.names else extra[n] for n in names], names=names)

def filter(D, region_code=None, region_name=None, voters_registered_min=None, voters_voted_le_voters_registered=False, foreign=None, ballots_valid_invalid_min=None):
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

def regions(D):
	return dict(np.unique(D[['region_code', 'region_name']], axis = 0).tolist())

def electoral_id(electoral_id = None, *, region_code = None, date = None, election_name = None, territory = None, station = None, **extra):
	fields = dict(
		region_code = r'[A-Z]{2}(-[A-Z]{3})?',
		date = r'\d{4}-\d{2}-\d{2}',
		election_name = r'[a-z]+',
		extra = r'([A-Z]+)[=]?([a-z0-9+]+)'
	)
	alias = dict(territory = ['T'], station = ['V'])
	val = lambda val, int_or_str = (lambda x: int(x) if x.isdigit() else x): list(map(int_or_str, val.split('+'))) if '+' in val else int_or_str(val)
	plusize = lambda k, val: alias.get(k, [k])[0] + '+'.join(map(str, val if isinstance(val, list) else [val]))
	if electoral_id:
		return dict((k, f) if k != 'extra' else (([k for k, a in alias.items() if m.group(1) in a] + [k])[0], val(m.group(2))) for f in electoral_id.split('_') for k, r in fields.items() for m in [re.fullmatch(r, f)] if m is not None)
	else:
		return '_'.join(str(f) for f in [region_code, plusize('territory', territory) if territory else None, plusize('station', station) if station else None, date, election_name] + [plusize(k, v) if v else None for k, v in extra.items()] if f is not None)
