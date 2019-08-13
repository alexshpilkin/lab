#!/usr/bin/env python3

# python3 ru_election_data.py --protocols shpilkin/protocols_227_json.txt --turnouts shpilkin/ik_turnouts_json.txt --precincts shpilkin/uiks_from_cikrf_json.txt --tsv _RU_2018-03-18_president.tsv.gz


import argparse
import collections
import csv
import io
import json
import math
import urllib.parse
import urllib.request

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
	return format(float(s.replace(' ', '')) if s else math.nan, '.6f')

def letters(s):
	return ''.join(c for c in s if c.isalpha() or c.isspace())


glossary = json.load(open(args.glossary))

bad = collections.defaultdict(set)
empty = {
	'region_code': None,
	'region_name': None,
	'foreign': -1,
	'tik_num': -1,
	'territory': None,
	'precinct': -1,
	'electoral_id': None,
	'commission_address': None,
	'commission_lat': math.nan,
	'commission_lon': math.nan,
	'station_address': None,
	'station_lat': math.nan,
	'station_lon': math.nan,
	'voters_voted': -1,
}
empty.update((k, -1) for k in glossary['fields'].keys())
empty.update((k, math.nan) for k in glossary['turnouts'].keys())

ik_turnouts = {}
for obj in jsons(argopen(args.turnouts)):
	key = obj['loc'][:-1] + [obj['ik_name']]
	val = {t.replace('.', ':'): format(v, '.4f') for t, v in obj['turnouts'].items()}
	ik_turnouts[tuple(key)] = val

locations = {}
for u in jsons(argopen(args.precincts)):
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

stations = []
for p in jsons(argopen(args.protocols)):
	if len(p['loc']) != 3:
		continue
	region_name, tik_name, uik_name = p['loc']
	uik_num = ''.join(c for c in uik_name if c.isdigit())
	tik_num, *tik_name = tik_name.split()
	tik_name = ' '.join(tik_name)
	if not uik_num:
		continue

	lines = p['data']
	if isinstance(lines, list):
		lines = {l['line_name']: l['line_val'] for l in lines}

	station = {f: sum(int(v)
	                  for pat in pats
	                  for k, v in lines.items()
	                  if pat in k)
	           for f, pats in glossary['fields'].items()}
	for f, pats in glossary['fields'].items():
		if not any(pat in k for pat in pats for k in lines.keys()):
			station[f] = -1
			bad[f].update(lines)

	region_code = [r
	               for r, pats in glossary['regions'].items()
	               for pat in pats
	               if pat in region_name]
	if len(region_code) == 1:
		region_code, = region_code
		region_name  = glossary['regions'][region_code][0]
	else:
		region_code = ''
		bad['regions'].add(region_name)

	station['region_code'] = region_code
	station['region_name'] = region_name
	station['precinct'] = int(uik_num)
	station['tik_num']  = int(tik_num)
	station['territory'] = tik_name.replace('Территориальная избирательная комиссия', 'ТИК').replace('города', 'г.').replace('района', 'р-на')
	station['vote'] = {letters(k): int(v)
	                   for k, v in lines.items()
	                   if letters(k).istitle() or 'партия' in k.lower()}
	station['voters_voted_early'] = station.get('voters_voted_early', 0)
	station['voters_voted_outside_station'] = station.get('voters_voted_outside_station', 0)
	station['voters_voted'] = (station['voters_voted_at_station'] + station['voters_voted_early'] + station['voters_voted_outside_station']) if station.get('voters_voted_at_station') is not None else None
	station['foreign'] = 1 if station['region_code'] == 'RU-FRN' else 0
	station['turnouts'] = ik_turnouts.get(tuple(p['loc']), None)

	station['commission_lat'] = math.nan
	station['commission_lon'] = math.nan
	station['station_lat'] = math.nan
	station['station_lon'] = math.nan
	station.update(locations.pop((station['region_code'], station['precinct']), {}))

	station['electoral_id'] = election_data.electoral_id(region_code = station['region_code'], date = args.date, election_name = args.election_name, station = station['precinct'], territory = station['tik_num'])

	stations.append(station)

for k in locations.keys():
	bad['precincts'].add(k)

if args.bad_json is not None:
	with open(args.bad_json, 'w', newline='\r\n') as file:
		json.dump({k: sorted(v) for k, v in bad.items()}, file, ensure_ascii=False, indent=2, sort_keys=True)


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
		s[k] = (s['turnouts'] or {}).get(v, math.nan)

if args.tsv is not None:
	fields  = list(empty.keys())
	fields += ['candidate{}_name'.format(c) for c in range(num_candidates)]
	fields += ['candidate{}_ballots'.format(c) for c in range(num_candidates)]

	with open(args.tsv, 'w', newline='\r\n') as out:
		wr = csv.DictWriter(out, fieldnames=fields, dialect=None, delimiter='\t', lineterminator='\n', quotechar=None, quoting=csv.QUOTE_NONE)
		wr.writeheader()
		for s in stations:
			s.pop('vote')
			s.pop('turnouts')
			wr.writerow(s)
