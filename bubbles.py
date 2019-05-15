#!/usr/bin/env python3

import numpy as np
import matplotlib.pyplot as plt

import election_data

def rlencode(inarray):  # Run-length encoding, <https://stackoverflow.com/a/32681075>
	ia = np.asarray(inarray)
	n = len(ia)
	if n == 0: 
		return (None, None, None)
	else:
		y = np.array(ia[1:] != ia[:-1])     # pairwise unequal (string safe)
		i = np.append(np.where(y), n - 1)   # must include last element posi
		z = np.diff(np.append(-1, i))       # run lengths
		p = np.cumsum(np.append(0, z))[:-1] # positions
		return (z, p, ia[i])

def plot(title, D, unit=1000):
	tlen, tidx, terr = rlencode(D.territory)
	tsum = np.insert(np.cumsum(tlen), 0, 0)
	assert np.unique(terr).shape == terr.shape

	plt.title(title + '\n', size=20, va='baseline')
	plt.scatter(np.arange(len(D.voters_registered)),
	            100 * D.leader / D.ballots_valid_invalid,
	            s=D.voters_registered / unit * 20,
	            alpha=0.5)

	plt.xlabel('Precinct')
	for x in tsum:
		plt.axvline(x, 0, 1, color='black', alpha=0.25, linewidth=1)
	ax1 = plt.gca()
	ax1.set_xlim((0, len(D.voters_registered)))
	ax1.set_xlabel('Precinct')
	ax1.set_xticks(tsum[:-1])
	ax1.set_xticklabels(D.precinct[tidx], ha='center', rotation=90)
	ax2 = ax1.twiny()
	ax2.set_xlim(ax1.get_xlim())
	ax2.set_xlabel('Territory')
	ax2.set_xticks(tsum[:-1])
	ax2.set_xticklabels(map(election_data.translit, terr),
	                    ha='left', rotation=60)
	ax2.tick_params(axis='x', rotation=60,
	                bottom=False, top=True,
	                labelbottom=False, labeltop=True)

	plt.ylabel('Leader’s result')
	plt.ylim(0, 100)

if __name__ == '__main__':
	import os
	import argparse
	import matplotlib
	matplotlib.use('Agg')

	parser = argparse.ArgumentParser()
	parser.add_argument('data', nargs='?', metavar='DATA', default='https://github.com/schitaytesami/lab/releases/download/data-v2/2018.tsv.gz', help='Data file to use, in TSV, NPY or NPZ format')
	parser.add_argument('-o', '--output', default='bubbles', help='Output directory')
	args = parser.parse_args()

	D = election_data.load(args.data)

	if not os.path.exists(args.output):
		os.mkdir(args.output)

	for region in np.unique(D.region):
		name = election_data.toident(region)
		print(region, flush=True)
		plt.figure(figsize=(12,4))
		plot(election_data.translit(region), election_data.filter(D, region=region))
		plt.savefig(os.path.join(args.output, name + '.png'),
		            bbox_inches='tight')
		plt.close()
