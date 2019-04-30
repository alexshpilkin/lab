import argparse
import json
import urllib.parse
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument('--protocols_json', default = 'https://github.com/schitaytesami/data/releases/download/20180909/2018_09_all_govs_protocols_json.txt')
parser.add_argument('--ik_turnouts_json', default = 'https://github.com/schitaytesami/data/releases/download/20180909/2018_09_all_govs_ik_turnouts_json.txt')
parser.add_argument('--glossary', default = 'ruelectiondata.json')
parser.add_argument('--election_num', default = 20180909, type = int)
parser.add_argument('--leftfront_dump', default = 'https://www.leftfront.org/elections/data/elections190112.sql')
args = parser.parse_args()

read_all_lines = lambda file_path: list(filter(bool, (urllib.request.urlopen if file_path.startswith('http') else (lambda p: open(p, 'rb')))(file_path).read().decode('utf-8').split('\n')))
protocols = list(map(json.loads, read_all_lines(args.protocols_json)))
ik_turnouts = list(map(json.loads, read_all_lines(args.ik_turnouts_json)))
glossary = json.load(open(args.glossary))
leftfront_dump = read_all_lines(args.leftfront_dump)
leftfront_dump_comissions_fields_begin = [i for i, l in enumerate(leftfront_dump) if 'CREATE TABLE `comissions`' in l][0]
leftfront_dump_comissions_fields_end = [i for i, l in enumerate(leftfront_dump) if i > leftfront_dump_comissions_fields_begin and 'PRIMARY KEY' in l][0]
leftfront_dump_comissions_fields = [l.split('`')[1] for l in leftfront_dump[(1 + leftfront_dump_comissions_fields_begin): leftfront_dump_comissions_fields_end]]
leftfront_dump_comissions = { (c['RegionID'], c['Number']) : c for c in [dict(zip(leftfront_dump_comissions_fields, c))  for l in leftfront_dump if 'INSERT INTO `comissions`' in l for c in eval(l[len('INSERT INTO `comissions` VALUES '):-1].replace('NULL', 'None'))] if c['Level'] == 4 }

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
	station['election_name'] = election_name
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
	c = leftfront_dump_comissions.get((station['region_num'], station['uik_num']))
	if c:
		station['address'] = c['Address']
		station['geo'] = (c['Lat'], c['Lng'])
	else:
		station['address'] = None
		station['geo'] = None

	res.append(station)

print(json.dumps(res, ensure_ascii = False, indent = 2, sort_keys = True))
