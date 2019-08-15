#!/usr/bin/env python3

# python3 ru_election_data.py --date 2018-03-18 --name president --protocols shpilkin/protocols_227_json.txt --turnouts shpilkin/ik_turnouts_json.txt --locations shpilkin/uiks_from_cikrf_json.txt _RU_2018-03-18_president.tsv.gz


import argparse
import collections
import csv
import io
import json
import math
import os.path
import urllib.parse
import urllib.request

import election_data


parser = argparse.ArgumentParser()
parser.add_argument('--glossary', default=os.path.join(os.path.dirname(__file__), 'ru_election_data.json'))
parser.add_argument('--protocols')
parser.add_argument('--turnouts')
parser.add_argument('--locations')
parser.add_argument('--bad-json')
parser.add_argument('--date')
parser.add_argument('--name')
parser.add_argument('output', nargs='?', metavar='OUTPUT')
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

def precinct(loc):
	if len(loc) < 3:
		return None
	region_name, tik_name, uik_name = loc
	region_code = regioncode(region_name)
	tik_num, *tik_name = tik_name.split()
	tik_num = int(tik_num)
	tik_name = ' '.join(tik_name).replace('Территориальная избирательная комиссия', 'ТИК').replace('города', 'г.').replace('района', 'р-на')
	uik_num = precinctnumber(uik_name)
	if uik_num < 0:
		return None

	p = precincts[region_code, uik_num]
	p['region_code'] = region_code
	if region_code:
		p['region_name'] = glossary['regions'][region_code][0]
		p['foreign'] = 1 if region_code.endswith('-FRN') else 0
	else:
		p['region_name'] = region_name
	p['tik_num'] = tik_num
	p['territory'] = tik_name
	p['precinct'] = uik_num
	p['electoral_id'] = election_data.electoral_id(region_code=region_code, date=args.date, election_name=args.name, station=uik_num, territory=tik_num)
	return p


glossary = json.load(open(args.glossary))
precincts = collections.defaultdict(lambda: dict(empty))
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
	'commission_lat': 'nan',
	'commission_lon': 'nan',
	'station_address': None,
	'station_lat': 'nan',
	'station_lon': 'nan',
	'voters_voted': -1,
}
empty.update((k, -1) for k in glossary['fields'].keys())
empty.update((k, math.nan) for k in glossary['turnouts'].keys())


# Turnouts

if args.turnouts is not None:
	for obj in jsons(argopen(args.turnouts)):
		p = precinct(obj['loc'][:-1] + [obj['ik_name']])
		if p is None:
			continue
		for k, t in glossary['turnouts'].items():
			p[k] = format(obj['turnouts'].get(t, math.nan), '.4f')


# Protocols

if args.protocols is not None:
	for obj in jsons(argopen(args.protocols)):
		p = precinct(obj['loc'])
		if p is None:
			continue

		lines = obj['data']
		if isinstance(lines, list):
			lines = {l['line_name']: l['line_val'] for l in lines}

		for f, pats in glossary['fields'].items():
			if not any(pat in k for pat in pats for k in lines.keys()):
				bad[f].update(lines)
				continue
			p[f] = sum(int(v)
				   for pat in pats
				   for k, v in lines.items()
				   if pat in k)

		p['vote'] = {letters(k): int(v)
			     for k, v in lines.items()
			     if letters(k).istitle() or 'партия' in k.lower()}

		if p['voters_voted_at_station'] >= 0:
			p['voters_voted'] = (p['voters_voted_at_station'] +
				             max(0, p.get('voters_voted_early', -1)) +
				             max(0, p.get('voters_voted_outside_station', -1)))


# Locations

if args.locations is not None:
	for obj in jsons(argopen(args.locations)):
		region_code = regioncode(obj['region'])
		uik_num = precinctnumber(obj['text'])
		p = precincts[region_code, uik_num]
		p['region_code'] = region_code
		if region_code:
			p['region_name'] = glossary['regions'][region_code][0]
			p['foreign'] = 1 if region_code.endswith('-FRN') else 0
		else:
			p['region_name'] = obj['region']

		p['precinct'] = uik_num
		p['commission_address'] = obj['address'].strip().replace('\t', ' ')
		p['commission_lat'] = format(coord(obj['coords']['lat']), '.6f')
		p['commission_lon'] = format(coord(obj['coords']['lon']), '.6f')
		p['station_address'] = obj['voteaddress'].strip().replace('\t', ' ')
		p['station_lat'] = format(coord(obj['votecoords']['lat']), '.6f')
		p['station_lon'] = format(coord(obj['votecoords']['lon']), '.6f')


# Postprocessing

num_candidates = max(len(p.get('vote', {})) for p in precincts.values())
for p in precincts.values():
	vote = p.pop('vote', {})
	for i, (k, v) in enumerate(vote.items()):
		p['candidate{}_name'.format(i)] = k
		p['candidate{}_ballots'.format(i)] = v
	for i in range(len(vote), num_candidates):
		p['candidate{}_name'.format(i)] = ''
		p['candidate{}_ballots'.format(i)] = -1

if args.bad_json is not None:
	with open(args.bad_json, 'w', newline='\r\n') as file:
		json.dump({k: sorted(v) for k, v in bad.items()}, file, ensure_ascii=False, indent=2, sort_keys=True)

fields  = list(empty.keys())
fields += ['candidate{}_name'.format(i) for i in range(num_candidates)]
fields += ['candidate{}_ballots'.format(i) for i in range(num_candidates)]

with open(args.output, 'w', newline='\r\n') as out:
	wr = csv.DictWriter(out, fieldnames=fields, dialect=None, delimiter='\t', lineterminator='\n', quotechar=None, quoting=csv.QUOTE_NONE)
	wr.writeheader()
	for p in precincts.values():
		wr.writerow(p)
