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
args = parser.parse_args()

read_all_lines = lambda file_path: list(filter(bool, (urllib.request.urlopen if file_path.startswith('http') else (lambda p: open(p, 'rb')))(file_path).read().decode('utf-8').split('\n')))
glossary = json.load(open(args.glossary))
protocols = list(map(json.loads, read_all_lines(args.protocols_jsonl)))
ik_turnouts = {''.join(s['loc']) : s for s in map(json.loads, read_all_lines(args.turnouts_jsonl))}
#uiks_from_cikrf = list(map(json.loads, read_all_lines(args.uiks_from_cikrf_json)))

sum_or_none = lambda xs: None if all(x is None for x in xs) else sum(x for x in xs if x is not None)
letters = lambda s: ''.join(c for c in s if c.isalpha() or c.isspace())

bad = collections.defaultdict(set)

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
	station['region_num'] = region_num
	station['tik_num']  = int(tik_num)
	station['tik_name'] = tik_name
	station['vote'] = {k_ : int(v) for k, v in lines.items() for k_ in [letters(k)] if k_.istitle()}
	station['voters_voted_early'] = station.get('voters_voted_early', 0)
	station['voters_voted_outside_station'] = station.get('voters_voted_outside_station', 0)
	station['voters_voted'] = (station['voters_voted_at_station'] + station['voters_voted_early'] + station['voters_voted_outside_station']) if station.get('voters_voted_at_station') is not None else None
	station['foreign'] = station['region_code'] == 'FRN'

	p['loc'][-1] = uik_name + ' ' + p['loc'][-1]
	station['turnouts'] = {k.replace('.', ':') : v for k, v in ik_turnouts.get(''.join(p['loc']), dict(turnouts = {}))['turnouts'].items()} or None

	stations.append(station)

for k in bad:
	bad[k] = list(sorted(bad[k]))
if args.bad_json is not None:
	with open(args.bad_json, 'w', newline='\r\n') as file:
		json.dump(bad, file, ensure_ascii=False, indent=2, sort_keys=True)

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

_str = 'U128'
dtype = [('election_name', _str), ('region_name', _str), ('region_code', _str), ('tik_name', _str), ('uik_num', int), ('tik_num', int), ('region_num', int), ('voters_registered', int), ('voters_voted', int), ('voters_voted_at_station', int), ('voters_voted_outside_station', int), ('voters_voted_early', int), ('ballots_valid', int), ('ballots_invalid', int), ('foreign', bool)] + [(k, float) for k in sorted(glossary['turnouts'])] + [(k, int) for k in sorted(vote_kv)]
arr = np.array([tuple(s[n] for n, t in dtype) for s in stations], dtype = dtype)

if args.npz is not None:
	np.savez_compressed(args.npz, arr)

np.savetxt(args.tsv, arr, comments='', header='\t'.join(arr.dtype.names), fmt='\t'.join({int: '%d', bool: '%d', _str: '%s', float: '%.4f'}[t] for n, t in dtype), delimiter='\t', newline='\r\n', encoding = 'utf-8')
