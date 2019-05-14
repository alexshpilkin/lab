import csv
import gzip
import io
import unicodedata
import urllib.request
import numpy as np

RU_REGIONS = {
	'RU-AMU' : 'Амурская область',
	'RU-ARK' : 'Архангельская область',
	'RU-AST' : 'Астраханская область',
	'RU-BEL' : 'Белгородская область',
	'RU-BRY' : 'Брянская область',
	'RU-VLA' : 'Владимирская область',
	'RU-VGG' : 'Волгоградская область',
	'RU-VLG' : 'Вологодская область',
	'RU-VOR' : 'Воронежская область',
	'RU-IVA' : 'Ивановская область',
	'RU-IRK' : 'Иркутская область',
	'RU-KGD' : 'Калининградская область',
	'RU-KLU' : 'Калужская область',
	'RU-KEM' : 'Кемеровская область',
	'RU-KIR' : 'Кировская область',
	'RU-KOS' : 'Костромская область',
	'RU-KGN' : 'Курганская область',
	'RU-KRS' : 'Курская область',
	'RU-LEN' : 'Ленинградская область',
	'RU-LIP' : 'Липецкая область',
	'RU-MAG' : 'Магаданская область',
	'RU-MOS' : 'Московская область',
	'RU-MUR' : 'Мурманская область',
	'RU-NIZ' : 'Нижегородская область',
	'RU-NGR' : 'Новгородская область',
	'RU-NVS' : 'Новосибирская область',
	'RU-OMS' : 'Омская область',
	'RU-ORE' : 'Оренбургская область',
	'RU-ORL' : 'Орловская область',
	'RU-PNZ' : 'Пензенская область',
	'RU-PSK' : 'Псковская область',
	'RU-ROS' : 'Ростовская область',
	'RU-RYA' : 'Рязанская область',
	'RU-SAM' : 'Самарская область',
	'RU-SAR' : 'Саратовская область',
	'RU-SAK' : 'Сахалинская область',
	'RU-SVE' : 'Свердловская область',
	'RU-SMO' : 'Смоленская область',
	'RU-TAM' : 'Тамбовская область',
	'RU-TVE' : 'Тверская область',
	'RU-TOM' : 'Томская область',
	'RU-TUL' : 'Тульская область',
	'RU-TYU' : 'Тюменская область',
	'RU-ULY' : 'Ульяновская область',
	'RU-CHE' : 'Челябинская область',
	'RU-YAR' : 'Ярославская область',
	'RU-AD'  : 'Адыгея', 
	'RU-BA'  : 'Башкортостан',
	'RU-BU'  : 'Бурятия',
	'RU-DA'  : 'Дагестан',
	'RU-IN'  : 'Ингушетия',
	'RU-KB'  : 'Кабардино-Балкария',
	'RU-KL'  : 'Калмыкия',
	'RU-KC'  : 'Карачаево-Черкесия',
	'RU-KR'  : 'Карелия',
	'RU-ME'  : 'Марий Эл',
	'RU-MO'  : 'Мордовия',
	'RU-AL'  : 'Республика Алтай',
	'RU-KO'  : 'Республика Коми',
	'RU-SA'  : 'Республика Саха',
	'RU-SE'  : 'Северная Осетия',
	'RU-TA'  : 'Татарстан',
	'RU-TY'  : 'Тыва',
	'RU-UD'  : 'Удмуртия',
	'RU-KK'  : 'Хакасия',
	'RU-CE'  : 'Чечня',
	'RU-CU'  : 'Чувашия',
	'RU-ALT' : 'Алтайский край',
	'RU-ZAB' : 'Забайкальский край',
	'RU-KAM' : 'Камчатский край',
	'RU-KDA' : 'Краснодарский край',
	'RU-KYA' : 'Красноярский край',
	'RU-PER' : 'Пермский край',
	'RU-PRI' : 'Приморский край',
	'RU-STA' : 'Ставропольский край',
	'RU-KHA' : 'Хабаровский край',
	'RU-NEN' : 'Ненецкий автономный округ',
	'RU-KHM' : 'Ханты-Мансийский автономный округ — Югра',
	'RU-CHU' : 'Чукотский автономный округ',
	'RU-YAN' : 'Ямало-Ненецкий автономный округ',
	'RU-SPE' : 'Санкт-Петербург',
	'RU-MOW' : 'Москва',
	'RU-YEV' : 'Еврейская автономная область'
}

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

def load(fileorurl, numpy=False, latin=False):
	file = (urllib.request.urlopen(fileorurl) if fileorurl.startswith('http') else open(fileorurl, 'rb')) if isinstance(fileorurl, str) else io.BufferedReader(fileorurl)
	with file:
		if numpy:
			table = np.load(io.BytesIO(file.read()))
			if isinstance(table, np.lib.npyio.NpzFile):
				table = table['arr_0']
		else:
			if file.peek(1)[:1] == b'\x1f':	# gzip magic
				file = gzip.GzipFile(fileobj=file)
			# https://www.iana.org/assignments/media-types/text/tab-separated-values
			rd = csv.DictReader(io.TextIOWrapper(file, newline='\r\n'),
			                    delimiter='\t',
			                    lineterminator='\n',
			                    quoting=csv.QUOTE_NONE)
			it = iter(rd)
			first = next(it)
			dtype = [(toident(name), '<i4' if value.isdigit() else '<f8' if value.replace('.', '', 1).isdigit() else '<U127') for name, value in zip(rd.fieldnames, first.values())]
			table = np.array([tuple(first.values())], dtype=dtype)
			for i, row in enumerate(it):
				if i + 1 >= len(table):
					table.resize(2*len(table))
				table[i + 1] = tuple(row.values())
			table.resize(i + 1)
		
	leader = table[[n for n in table.dtype.names if 'putin' in n][0]]
	territory = np.chararray.replace(table['tik_name'], 'Территориальная избирательная комиссия', 'ТИК')
	return np.rec.fromarrays([leader, table['voters_registered'], table['voters_voted'], table['ballots_valid'] + table['ballots_invalid'], table['region_name'], territory, table['uik_num'], table['foreign']], names=COLUMNS)

def filter(D, region=None, voters_registered_min=None, voters_voted_le_voters_registered=False, foreign=None, ballots_valid_invalid_min=None):
	idx = np.full(len(D), True)

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
