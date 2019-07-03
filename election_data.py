import re
import csv
import gzip
import io
import unicodedata
import urllib.request
import numpy as np
import numpy.lib.recfunctions # http://pyopengl.sourceforge.net/pydoc/numpy.lib.recfunctions.html

RU_LEADER = ['Путин', 'Медведев']
RU_TRANSLIT =  ('АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ'
				'абвгдеёжзийклмнопрстуфхцчшщъыьэюя',
				'ABVGDEËŽZIJKLMNOPRSTUFHCČŠŜ"Y\'ÈÛÂ'
				'abvgdeëžzijklmnoprstufhcčšŝ"y\'èûâ')

def load(fileorurl, max_string_size = 64, encoding = 'utf-8', latin = False, leader = RU_LEADER):
	if isinstance(fileorurl, str):
		file = urllib.request.urlopen(fileorurl) if fileorurl.startswith('http') else open(fileorurl, 'rb')
		fileorurl = gzip.open(file, 'rt') if fileorurl.endswith('.gz') else io.TextIOWrapper(file)

	#head = np.genfromtxt(io.BytesIO(b), max_rows = 2 if has_names else 1, delimiter = delimiter, names = True if has_names else None, dtype = None, encoding = encoding)
	rd = csv.reader(fileorurl, delimiter = '\t', lineterminator='\n')
	it = iter(rd)
	fieldnames = next(it)
	first = next(it)
	dtype = [(name, '<i4' if value.isdigit() else '<f8' if value.replace('.', '', 1).isdigit() or value == 'nan' else f'<U{max_string_size}') for name, value in zip(fieldnames, first)]
	T = np.array([tuple(first)], dtype=dtype)
	for i, row in enumerate(it, start=1):
		if i >= len(T):
			T.resize(2 * len(T))
		T[i] = tuple(int(v) if dtype[j][1][1] == 'i' else float(v) if dtype[j][1][1] == 'f' else v for j, v in enumerate(row))
	T.resize(i)

	extra = dict(
		ballots_valid_invalid = T['ballots_valid'] + T['ballots_invalid'], 
		turnout = (T['voters_voted_at_station'] + T['voters_voted_early'] + T['voters_voted_outside_station']).astype(np.float32) / T['voters_registered'],
	)
	extra.update({name.replace('_name', '_hash') : np.fromiter(map(hash, T[name]), dtype = np.int64, count = len(T)) for name in T.dtype.names if name.startswith('candidate') and name.endswith('_name')})

	D = numpy.lib.recfunctions.append_fields(T.view(np.recarray), list(extra.keys()), [extra[k] for k in extra.keys()], asrecarray = True)
	D = promote_candidates_to_columns(D, leader = leader, latin = latin)

	#def shrink(x):
	##	max_len = max(map(len, x))
	##	return (x.copy().view('U1').reshape(len(x), -1)[:, :max_len].copy().view(('U', max_len)) if max_len > 0 and max_len < x.shape[-1] else x).squeeze()

	return D

def latinize(s, safe = False, T = {ord(a): ord(b) for a, b in zip(*RU_TRANSLIT)}, S = dict([(' ', '_')] + [(ord(c), None) for c in ''',."'()'''])):
	#s = unicodedata.normalize('NFD', translit(s)).encode('ascii', 'ignore').decode('ascii')
	return s.translate(T) if not safe else s.translate(T).translate(S).lower()

def promote_candidates_to_columns(D, leader = [], latin = False):
	latinize_ = lambda s, **kwargs: s if latin else latinize(s, safe = True)
	name_map = {name.replace('_hash', '_ballots') : 'candidate_' + latinize_(D[name.replace('_hash', '_name')][0].replace(' ', '_')) for name in D.dtype.names if name.endswith('_hash') and len(np.unique(D[name])) == 1}
	D = np.lib.recfunctions.rename_fields(D, name_map)
	D = np.lib.recfunctions.append_fields(D, ['leader'], [D[n] for n in D.dtype.names if any(l.lower() in n.lower() for l in leader)], asrecarray = True)
	return D

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
	spacize = lambda o: str(o).replace(' ', '-')
	plusize = lambda k, val: alias.get(k, [k])[0] + '+'.join(map(spacize, val if isinstance(val, list) else [spacize(val)]))
	if electoral_id:
		return dict((k, f) if k != 'extra' else (([k for k, a in alias.items() if m.group(1) in a] + [k])[0], val(m.group(2))) for f in electoral_id.split('_') for k, r in fields.items() for m in [re.fullmatch(r, f)] if m is not None)
	else:
		return '_'.join(str(f) for f in [region_code, plusize('territory', territory) if territory else None, plusize('station', station) if station else None, date, election_name] + [plusize(k, v) if v else None for k, v in extra.items()] if f is not None)
