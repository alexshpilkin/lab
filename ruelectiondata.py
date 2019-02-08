import argparse
import json
import urllib.parse

parser = argparse.ArgumentParser()
parser.add_argument('--protocols_json', default = 'https://github.com/schitaytesami/data/releases/download/20180909/2018_09_all_govs_protocols_json.txt')
parser.add_argument('--ik_turnouts_json', default = 'https://github.com/schitaytesami/data/releases/download/20180909/2018_09_all_govs_ik_turnouts_json.txt')
parser.add_argument('--glossary', default = 'ruelectiondata.json')
parser.add_argument('--election_num', default = 20180909, type = int)
args = parser.parse_args()

read_all_lines = lambda file_path = (urllib.request.urlopen if args.stations.startswith('http') else (lambda p: open(p, 'rb')))(file_path).read().decode('utf-8').split('\n')
protocols = list(map(json.loads, read_all_lines(args.protocols_json)))
ik_turnouts = list(map(json.loads, read_all_lines(args.ik_turnouts_json)))
glossary = json.load(open(args.glossary))


bad = []
res = []

for p in protocols:
	election_name, tik_name, uik_name = p['loc']
	uik_name = ''.join(c for c in uik_name if c.isdigit())
	tik_splitted = tik_name.split()
	tik_num, tik_name = tik_splitted[0], ' '.join(tik_splitted[1:])
	region_num = int(urllib.parse.parse_qs(p['url'])['region'][0])

	if not uik_name:
		continue

	sum_or_none = lambda xs: None if all(x is None for x in xs) else sum(x for x in xs if x is not None)

	station = {k : sum_or_none([(int(v) if v is not None else v) for v in map({l['line_name'] : l['line_val'] for l in p['data']}.get, glossary[k])]) for k in glossary}
	station['region_name'] = election_name
	station['uik_num'] = int(uik_name)
	station['region_num'] = region_num
	station['election_num'] = args.election_num
	station['tik_num']  = int(tik_num)
	station['tik_name'] = tik_name
	station['vote'] = {l['line_name'] : int(l['line_val']) for l in p['data'] if l['line_name'].istitle()}
	voters_voted_at_station, voters_voted_early, voters_voted_outside_station = list(map(station.get, ['voters_voted_at_station', 'voters_voted_early', 'voters_voted_outside_station']))
	station['voters_voted_early'] = voters_voted_early or 0
	station['voters_voted_outside_station'] = voters_voted_outside_station or 0
	station['voters_voted'] = (station['voters_voted_at_station'] + station['voters_voted_early'] + station['voters_voted_outside_station']) if voters_voted_at_station is not None else None

	res.append(station)

print(json.dumps(res, ensure_ascii = False, indent = 2, sort_keys = True))

print('\n'.join(sorted(set(bad))))
