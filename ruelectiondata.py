import argparse
import json
import urllib.parse
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument('--protocols_json', default = 'https://github.com/schitaytesami/data/releases/download/20180318/protocols_227_json.txt')
parser.add_argument('--ik_turnouts_json', default = 'https://github.com/schitaytesami/data/releases/download/20180318/ik_turnouts_json.txt')
parser.add_argument('--uiks_from_cikrf_json', default = 'https://github.com/schitaytesami/data/releases/download/20180318/uiks_from_cikrf_json.txt')
parser.add_argument('--glossary', default = 'ruelectiondata.json')
parser.add_argument('--election_num', default = 20180318, type = int)
args = parser.parse_args()

read_all_lines = lambda file_path: list(filter(bool, (urllib.request.urlopen if file_path.startswith('http') else (lambda p: open(p, 'rb')))(file_path).read().decode('utf-8').split('\n')))
glossary = json.load(open(args.glossary))

protocols = list(map(json.loads, read_all_lines(args.protocols_json)))
ik_turnouts = {''.join(s['loc']) : s for s in map(json.loads, read_all_lines(args.ik_turnouts_json))}
uiks_from_cikrf = list(map(json.loads, read_all_lines(args.uiks_from_cikrf_json)))

res = []
for p in protocols:
	election_name, tik_name, uik_name = (p['loc'] + ['', '', ''])[:3]
	uik_name = ''.join(c for c in uik_name if c.isdigit())
	tik_splitted = tik_name.split()
	tik_num, tik_name = tik_splitted[0], ' '.join(tik_splitted[1:])
	region_num = int(urllib.parse.parse_qs(p['url'])['region'][0])

	if not uik_name:
		continue

	sum_or_none = lambda xs: None if all(x is None for x in xs) else sum(x for x in xs if x is not None)
	letters = lambda s: ''.join(c for c in s if c.isalpha() or c.isspace())
	
	lines = p['data']
	#lines = {l['line_name'] : l['line_val'] for l in p['data']}
	lines_get = lambda g: ([v for k, v in lines.items() if g in k] + [None])[0]

	station = {k : sum_or_none([(int(v) if v is not None else v) for v in map(lines_get, glossary[k]) ]) for k in glossary}

	station['election_name'] = election_name
	station['uik_num'] = int(uik_name)
	station['region_num'] = region_num
	station['election_num'] = args.election_num
	station['tik_num']  = int(tik_num)
	station['tik_name'] = tik_name
	station['vote'] = {k_ : int(v) for k, v in lines.items() for k_ in [letters(k)] if k_.istitle()}
	voters_voted_at_station, voters_voted_early, voters_voted_outside_station = list(map(station.get, ['voters_voted_at_station', 'voters_voted_early', 'voters_voted_outside_station']))
	station['voters_voted_early'] = voters_voted_early or 0
	station['voters_voted_outside_station'] = voters_voted_outside_station or 0
	station['voters_voted'] = (station['voters_voted_at_station'] + station['voters_voted_early'] + station['voters_voted_outside_station']) if voters_voted_at_station is not None else None

	p['loc'][-1] = uik_name + ' ' + p['loc'][-1]
	station['turnouts'] = {k.replace('.', ':') : v for k, v in ik_turnouts.get(''.join(p['loc']), dict(turnouts = {}))['turnouts'].items()} or None

	res.append(station)

print(json.dumps(res, ensure_ascii = False, indent = 2, sort_keys = True))
