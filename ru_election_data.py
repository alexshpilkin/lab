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
	return float(s.replace(' ', '')) if s else math.nan

def letters(s):
	return ''.join(c for c in s if c.isalpha() or c.isspace())


glossary = json.load(open(args.glossary))

def regioncode(name):
	codes = [r
	         for r, pats in glossary['regions'].items()
	         for pat in pats
	         if pat in name]
	if len(codes) != 1:
		bad['regions'].add(name)
	return codes[0] if codes else ''

def precinctnumber(name):
	num = ''.join(c for c in name if c.isdigit())
	return int(num) if num else -1

empty = {
	'region_code': None,
	'region_name': None,
	'foreign': -1,
	'tik_num': -1,
	'territory': None,
	'precinct': -1,
	'electoral_id': None,
	'commission_address': None,
	'commission_lat': 'nan',
	'commission_lon': 'nan',
	'station_address': None,
	'station_lat': 'nan',
	'station_lon': 'nan',
	'voters_voted': -1,
}
empty.update((k, -1) for k in glossary['fields'].keys())
empty.update((k, math.nan) for k in glossary['turnouts'].keys())


precincts = collections.defaultdict(dict)
bad = collections.defaultdict(set)


# Turnouts

for obj in jsons(argopen(args.turnouts)):
	if len(obj['loc']) < 3:
		continue
	key = regioncode(obj['loc'][0]), precinctnumber(obj['ik_name'])

	for k, t in glossary['turnouts'].items():
		precincts[key][k] = format(obj['turnouts'].get(t, math.nan), '.4f')


locations = {}
for u in jsons(argopen(args.precincts)):
	key = regioncode(u['region']), precinctnumber(u['text'])

	precinct = {}
	precinct['commission_address'] = u['address'].strip().replace('\t', ' ')
	precinct['commission_lat'] = format(coord(u['coords']['lat']), '.6f')
	precinct['commission_lon'] = format(coord(u['coords']['lon']), '.6f')
	precinct['station_address'] = u['voteaddress'].strip().replace('\t', ' ')
	precinct['station_lat'] = format(coord(u['votecoords']['lat']), '.6f')
	precinct['station_lon'] = format(coord(u['votecoords']['lon']), '.6f')

	locations[key] = precinct

stations = []
for p in jsons(argopen(args.protocols)):
	if len(p['loc']) != 3:
		continue
	region_name, tik_name, uik_name = p['loc']
	region_code = regioncode(region_name)
	if region_code:
		region_name = glossary['regions'][region_code][0]
	uik_num = precinctnumber(uik_name)
	tik_num, *tik_name = tik_name.split()
	tik_name = ' '.join(tik_name)
	if uik_num < 0:
		continue
	key = region_code, uik_num

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

	station['region_code'] = region_code
	station['region_name'] = region_name
	station['precinct'] = uik_num
	station['tik_num']  = tik_num
	station['territory'] = tik_name.replace('Территориальная избирательная комиссия', 'ТИК').replace('города', 'г.').replace('района', 'р-на')
	station['vote'] = {letters(k): int(v)
	                   for k, v in lines.items()
	                   if letters(k).istitle() or 'партия' in k.lower()}
	station['voters_voted_early'] = station.get('voters_voted_early', 0)
	station['voters_voted_outside_station'] = station.get('voters_voted_outside_station', 0)
	station['voters_voted'] = (station['voters_voted_at_station'] + station['voters_voted_early'] + station['voters_voted_outside_station']) if station.get('voters_voted_at_station') is not None else None
	station['foreign'] = 1 if station['region_code'] == 'RU-FRN' else 0

	for k in glossary['turnouts'].keys():
		station[k] = 'nan'
	station.update(precincts.get(key, {}))
	station['commission_lat'] = 'nan'
	station['commission_lon'] = 'nan'
	station['station_lat'] = 'nan'
	station['station_lon'] = 'nan'
	station.update(locations.pop(key, {}))

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
		s[f'candidates{c}_ballots'] = -1

if args.tsv is not None:
	fields  = list(empty.keys())
	fields += ['candidate{}_name'.format(c) for c in range(num_candidates)]
	fields += ['candidate{}_ballots'.format(c) for c in range(num_candidates)]

	with open(args.tsv, 'w', newline='\r\n') as out:
		wr = csv.DictWriter(out, fieldnames=fields, dialect=None, delimiter='\t', lineterminator='\n', quotechar=None, quoting=csv.QUOTE_NONE)
		wr.writeheader()
		for s in stations:
			s.pop('vote')
			wr.writerow(s)
