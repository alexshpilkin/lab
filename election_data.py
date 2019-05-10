import csv
import gzip
import io
import unicodedata
import urllib.request
import numpy as np

COLUMNS = ('leader', 'voters_registered', 'voters_voted', 'ballots_valid_invalid', 'region', 'territory', 'precinct', 'foreign')

TRANSLIT = ('АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ'
	'абвгдеёжзийклмнопрстуфхцчшщъыьэюя',
	'ABVGDEËŽZIJKLMNOPRSTUFHCČŠŜ"Y\'ÈÛÂ'
	'abvgdeëžzijklmnoprstufhcčšŝ"y\'èûâ')	# ISO 9:1995
TRANSLIT = {ord(a): ord(b) for a, b in zip(*TRANSLIT)}

def translit(s):
	return s.translate(TRANSLIT)

def toident(s):
	s = unicodedata.normalize('NFD', translit(s)).encode('ascii', 'ignore').decode('ascii')
	return s.lower().replace(' ', '_').translate({ord(c) : None for c in ''',."'()'''})

def load(fileorurl, numpy = False, latin = False):
	def urlopen(fileorurl):
		if isinstance(fileorurl, io.BufferedIOBase):
			return io.BufferedReader(fileorurl)
		elif fileorurl.startswith('http'):
			return urllib.request.urlopen(fileorurl)
		else:
			return open(fileorurl, 'rb')

	def flt(table, include, exclude=()):
		return [col
				for col in table.dtype.names
				if any(toident(f) in col for f in include) and
				not any(toident(f) in col for f in exclude)]


	if numpy:
		with urlopen(fileorurl) as file:
			table = np.load(io.BytesIO(file.read()))
			if isinstance(table, np.lib.npyio.NpzFile):
				table = table['arr_0']
	else:
		with urlopen(fileorurl) as file:
			if file.peek(1)[:1] == b'\x1f':	# gzip magic
				file = gzip.GzipFile(fileobj=file)
			rd = csv.DictReader(io.TextIOWrapper(file, newline='\r\n'), delimiter = '\t', lineterminator = '\n', quoting = csv.QUOTE_NONE) # IETF format: https://www.iana.org/assignments/media-types/text/tab-separated-values
			it = iter(rd)
			first = next(it)
			types = [(toident(name), '<i4' if value.isdigit() else '<f8' if value.replace('.', '', 1).isdigit() else '<U127') for name, value in zip(rd.fieldnames, first.values())]
			table = np.array([tuple(first.values())], dtype=types)
			for i, row in enumerate(it):
				if i + 1 >= len(table):
					table.resize(2*len(table))
				table[i + 1] = tuple(row.values())
			table.resize(i + 1)
		
	leader = np.squeeze(table[flt(table, {'Путин', 'Единая Россия', 'Медведев'})[0]])
	voters_registered = np.squeeze(table[flt(table, {'Число избирателей, включенных', 'Число избирателей, внесенных'})[0]])
	voters_voted = np.sum(np.vstack([table[c] for c in flt(table, {'бюллетеней, выданных'})]).T, axis=1)
	ballots_valid_invalid = np.sum(np.vstack([table[c] for c in flt(table, {'действительных', 'недействительных'}, {'отметок'})]).T, axis=1)
	region		= table['region']
	territory = np.chararray.replace(table['tik'], 'Территориальная избирательная комиссия', 'ТИК')
	precinct	= table['uik']
	foreign = np.array(['Зарубеж' in s or 'за пределами' in s for s in region])
	return np.rec.fromarrays([leader, voters_registered, voters_voted, ballots_valid_invalid, region, territory, precinct, foreign], names=COLUMNS)

def filter(D, region = None, voters_registered_min = None, voters_voted_le_voters_registered = False, foreign = None, ballots_valid_invalid_min = None):
	idx = np.full(len(D), True)

	if region is not None:
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
