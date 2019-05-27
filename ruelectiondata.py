#!/usr/bin/env python3

import collections
import argparse
import json
import urllib.parse
import urllib.request
import numpy as np

import election_data

parser = argparse.ArgumentParser()
parser.add_argument('--glossary', default = 'ruelectiondata.json')
parser.add_argument('--protocols-jsonl', default = 'https://github.com/schitaytesami/data/releases/download/20180318/protocols_227_json.txt')
parser.add_argument('--turnouts-jsonl', default = 'https://github.com/schitaytesami/data/releases/download/20180318/ik_turnouts_json.txt')
parser.add_argument('--precincts-jsonl', default = 'https://github.com/schitaytesami/data/releases/download/20180318/uiks_from_cikrf_json.txt')
parser.add_argument('--json')
parser.add_argument('--npz')
parser.add_argument('--tsv')
parser.add_argument('--bad-json')
parser.add_argument('--date', default = '2018-03-18')
parser.add-argument('--election-name', default = 'president')
args = parser.parse_args()

read_all_lines = lambda file_path: filter(bool, (urllib.request.urlopen if file_path.startswith('http') else (lambda p: open(p, 'rb')))(file_path).read().decode('utf-8').split('\n'))
glossary = json.load(open(args.glossary))
protocols = map(json.loads, read_all_lines(args.protocols_jsonl))
ik_turnouts = {''.join(s['loc']) : s for s in map(json.loads, read_all_lines(args.turnouts_jsonl))}
uiks_from_cikrf = map(json.loads, read_all_lines(args.precincts_jsonl))

bad = collections.defaultdict(set)

coord = lambda s: float(s.replace(' ', '')) if s else np.nan
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
	precinct['members'] = [{'name': m['ФИО'],
	                        'position': {'Председатель': 'chairman', 'Зам.председателя': 'vice-chairman', 'Секретарь': 'secretary', 'Член': 'member'}[m['Статус']],
	                        'delegated_by': m['Кем предложен в состав комиссии']}
	                       for m in u['members']]

	locations[(region, number)] = precinct

sum_or_none = lambda xs: None if all(x is None for x in xs) else sum(x for x in xs if x is not None)
letters = lambda s: ''.join(c for c in s if c.isalpha() or c.isspace())

stations = []
for p in protocols:
	election_name, tik_name, uik_name = (p['loc'] + ['', '', ''])[:3]
	uik_name = ''.join(c for c in uik_name if c.isdigit())
	tik_splitted = tik_name.split()
	tik_num, tik_name = tik_splitted[0], ' '.join(tik_splitted[1:])
	region_num = int(urllib.parse.parse_qs(p['url'])['region'][0])
	region_name = election_name

	if not uik_name:
		continue

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

	station['election_name'] = election_name
	station['region_name'] = glossary['regions'].get(station['region_code'], [region_name])[0]
	station['uik_num'] = int(uik_name)
	station['tik_num']  = int(tik_num)
	station['tik_name'] = tik_name.replace('Территориальная избирательная комиссия', 'ТИК')
	station['vote'] = {k_ : int(v) for k, v in lines.items() for k_ in [letters(k)] if k_.istitle()}
	station['voters_voted_early'] = station.get('voters_voted_early', 0)
	station['voters_voted_outside_station'] = station.get('voters_voted_outside_station', 0)
	station['voters_voted'] = (station['voters_voted_at_station'] + station['voters_voted_early'] + station['voters_voted_outside_station']) if station.get('voters_voted_at_station') is not None else None
	station['foreign'] = station['region_code'] == 'FRN'

	p['loc'][-1] = uik_name + ' ' + p['loc'][-1]
	station['turnouts'] = {k.replace('.', ':') : v for k, v in ik_turnouts.get(''.join(p['loc']), dict(turnouts = {}))['turnouts'].items()} or None

	station.update(locations.pop((station['region_code'], station['uik_num']), {}))

	station['electoral_id'] = election_data.electoral_id(region_code = station['region_code'], date = args.date, election_name = args.election_name)
	stations.append(station)

for k in locations.keys():
	bad['precincts'].add(k)

if args.bad_json is not None:
	with open(args.bad_json, 'w', newline='\r\n') as file:
		json.dump({k : list(sorted(v)) for k, v in bad.items()}, file, ensure_ascii=False, indent=2, sort_keys=True)

if args.json is not None:
	with open(args.json, 'w', newline='\r\n') as file:
		json.dump(stations, file, ensure_ascii=False, indent=2, sort_keys=True)

vote_kv = {'ballots_' + election_data.toident(k.lower()): k
           for s in stations for k in s['vote']}

for s in stations:
	for k, v in glossary['turnouts'].items():
		s[k] = (s['turnouts'] or {}).get(v, np.nan)
	for k, v in vote_kv.items():
		s[k] = (s['vote'] or {}).get(v, 0)

field_string_type = lambda field: ('S' if all(s.get(field, '').isascii() for s in stations) else 'U') + str(max(len(s.get(field, '')) for s in stations))
dtype = [(field, field_string_type(field)) for field in ['region_code', 'region_name', 'election_name', 'tik_name', 'commission_address', 'station_address', 'electoral_id']] + [('tik_num', int), ('uik_num', int), ('foreign', bool), ('commission_lat', float), ('commission_lon', float), ('station_lat', float), ('station_lon', float), ('voters_registered', int), ('voters_voted', int), ('voters_voted_at_station', int), ('voters_voted_outside_station', int), ('voters_voted_early', int), ('ballots_valid', int), ('ballots_invalid', int)] + [(k, np.float32) for k in sorted(glossary['turnouts'])] + [(k, int) for k in sorted(vote_kv)]

if args.npz is not None:
	dtype_no_address = [(n, t) for n, t in dtype if 'address' not in n]
	arr = np.array([tuple(s.get(n, "" if isinstance(t, str) else np.nan) for n, t in dtype_no_address) for s in stations], dtype=dtype_no_address)
	np.savez_compressed(args.npz, arr)

if args.tsv is not None:
	arr = np.array([tuple(s.get(n, "" if isinstance(t, str) else np.nan) for n, t in dtype) for s in stations], dtype=dtype)
	np.savetxt(args.tsv, arr, comments='', header='\t'.join(arr.dtype.names), fmt='\t'.join({int: '%d', bool: '%d', float: '%.6f', np.float32: '%.4f'}.get(t, '%s') for n, t in dtype), delimiter='\t', newline='\r\n', encoding='utf-8')
