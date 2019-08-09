#!/usr/bin/env python3

# python3 ru_election_data.py --protocols shpilkin/protocols_227_json.txt --turnouts shpilkin/ik_turnouts_json.txt --precincts shpilkin/uiks_from_cikrf_json.txt --tsv _RU_2018-03-18_president.tsv.gz


import collections
import argparse
import io
import json
import urllib.parse
import urllib.request
import numpy as np

import election_data

parser = argparse.ArgumentParser()
parser.add_argument('--glossary', default = 'ru_election_data.json')
parser.add_argument('--protocols', default = 'https://github.com/schitaytesami/data/releases/download/20180318/protocols_227_json.txt')
parser.add_argument('--turnouts', default = 'https://github.com/schitaytesami/data/releases/download/20180318/ik_turnouts_json.txt')
parser.add_argument('--precincts', default = 'https://github.com/schitaytesami/data/releases/download/20180318/uiks_from_cikrf_json.txt')
parser.add_argument('--tsv')
parser.add_argument('--bad-json')
parser.add_argument('--date', default = '2018-03-18')
parser.add_argument('--election-name', default = 'president')
args = parser.parse_args()

def argopen(url):
	return urllib.request.urlopen(url) if '//' in url else open(url, 'rb')

def jsons(file):
	# TODO gzip, json-seq support?
	file = io.TextIOWrapper(file, encoding='utf-8')
	return (json.loads(line) for line in file if line)

def coord(s):
	return float(s.replace(' ', '')) if s else np.nan

glossary = json.load(open(args.glossary))
protocols = jsons(argopen(args.protocols))
uiks_from_cikrf = jsons(argopen(args.precincts))

bad = collections.defaultdict(set)

ik_turnouts = {}
for obj in jsons(argopen(args.turnouts)):
	key = obj['loc'][:-1] + [obj['ik_name']]
	val = {t.replace('.', ':'): v for t, v in obj['turnouts'].items()}
	ik_turnouts[tuple(key)] = val

locations = {}
for u in uiks_from_cikrf:
	region = ([k for k, v in glossary['regions'].items() for vv in v if vv in u['region']] + [None])[0]
	number = int(''.join(c for c in u['text'] if c.isdigit()))

	if region is None:
		bad['regions'].add(u['region'])

	precinct = {}
	precinct['commission_address'] = u['address'].strip().replace('\t', ' ')
	precinct['commission_lat'] = coord(u['coords']['lat'])
	precinct['commission_lon'] = coord(u['coords']['lon'])
	precinct['station_address'] = u['voteaddress'].strip().replace('\t', ' ')
	precinct['station_lat'] = coord(u['votecoords']['lat'])
	precinct['station_lon'] = coord(u['votecoords']['lon'])

	locations[region, number] = precinct

sum_or_none = lambda xs: None if all(x is None for x in xs) else sum(x for x in xs if x is not None)
letters = lambda s: ''.join(c for c in s if c.isalpha() or c.isspace())

stations = []
for p in protocols:
	if len(p['loc']) != 3:
		continue
	region_name, tik_name, uik_name = p['loc']
	uik_name = ''.join(c for c in uik_name if c.isdigit())
	tik_num, *tik_name = tik_name.split()
	tik_name = ' '.join(tik_name)
	if not uik_name:
		continue
	region_num = int(urllib.parse.parse_qs(p['url'])['region'][0])

	lines = p['data']
	if isinstance(lines, list):
		lines = {l['line_name'] : l['line_val'] for l in lines}

	lines_get = lambda g: ([v for k, v in lines.items() if g in k] + [None])[0]

	station = {k : sum_or_none([(int(v) if v is not None else v) for v in map(lines_get, glossary['fields'][k]) ]) for k in glossary['fields']}
	for k, v in station.items():
		if v is None:
			bad[k].update(lines)

	station['region_code'] = ([k for k, v in glossary['regions'].items() for vv in v if vv in region_name] + [None])[0]
	if station['region_code'] is None:
		bad['regions'].add(region_name)

	station['region_name'] = glossary['regions'].get(station['region_code'], [region_name])[0]
	station['precinct'] = int(uik_name)
	station['tik_num']  = int(tik_num)
	station['territory'] = tik_name.replace('Территориальная избирательная комиссия', 'ТИК').replace('города', 'г.').replace('района', 'р-на')
	station['vote'] = {k_ : int(v) for k, v in lines.items() for k_ in [letters(k)] if k_.istitle()}
	station['voters_voted_early'] = station.get('voters_voted_early', 0)
	station['voters_voted_outside_station'] = station.get('voters_voted_outside_station', 0)
	station['voters_voted'] = (station['voters_voted_at_station'] + station['voters_voted_early'] + station['voters_voted_outside_station']) if station.get('voters_voted_at_station') is not None else None
	station['foreign'] = station['region_code'] == 'RU-FRN'
	station['turnouts'] = ik_turnouts.get(tuple(p['loc']), None)

	station.update(locations.pop((station['region_code'], station['precinct']), {}))

	station['electoral_id'] = election_data.electoral_id(region_code = station['region_code'], date = args.date, election_name = args.election_name, station = station['precinct'], territory = station['territory'])

	stations.append(station)

for k in locations.keys():
	bad['precincts'].add(k)

if args.bad_json is not None:
	with open(args.bad_json, 'w', newline='\r\n') as file:
		json.dump({k : list(sorted(v)) for k, v in bad.items()}, file, ensure_ascii=False, indent=2, sort_keys=True)

vote_kv = {'ballots_' + k.lower().replace(' ', '_') : k for s in stations for k in s['vote']}


num_candidates = max(len(s['vote']) for s in stations)
for s in stations:
	for c, (k, v) in enumerate(s['vote'].items()):
		s[f'candidate{c}_name'] = k
		s[f'candidate{c}_ballots'] = v
	for c in range(len(s['vote']), num_candidates):
		s[f'candidate{c}_name'] = ''
		s[f'candidates{c}_ballots'] = 0


for s in stations:
	for k, v in glossary['turnouts'].items():
		s[k] = (s['turnouts'] or {}).get(v, np.nan)
	for k, v in vote_kv.items():
		s[k] = (s['vote'] or {}).get(v, 0)
field_string_type = lambda field: 'U' + str(max(len(s.get(field, '')) for s in stations))
candidate_fields = [(f'candidate{c}_name', field_string_type(f'candidate{c}_name')) for c in range(num_candidates)] + [(f'candidate{c}_ballots', int) for c in range(num_candidates)]
dtype = [(field, field_string_type(field)) for field in ['region_code', 'region_name', 'territory', 'commission_address', 'station_address', 'electoral_id']] + [('tik_num', int), ('precinct', int), ('foreign', bool), ('commission_lat', float), ('commission_lon', float), ('station_lat', float), ('station_lon', float), ('voters_registered', int), ('voters_voted', int), ('voters_voted_at_station', int), ('voters_voted_outside_station', int), ('voters_voted_early', int), ('ballots_valid', int), ('ballots_invalid', int)] + [(k, np.float32) for k in sorted(glossary['turnouts'])] + candidate_fields # [(k, int) for k in sorted(vote_kv)]

if args.tsv is not None:
	arr = np.array([tuple(s.get(n, "" if isinstance(t, str) else np.nan) for n, t in dtype) for s in stations], dtype=dtype)
	np.savetxt(args.tsv, arr, comments='', header='\t'.join(arr.dtype.names), fmt='\t'.join({int: '%d', bool: '%d', float: '%.6f', np.float32: '%.4f'}.get(t, '%s') for n, t in dtype), delimiter='\t', encoding='utf-8')
