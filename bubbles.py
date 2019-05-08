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

def plot(D, region):
	idx = D.region == region
	tlen, tidx, terr = rlencode(D.territory[idx])
	tsum = np.insert(np.cumsum(tlen), 0, 0)
	assert np.unique(terr).shape == terr.shape

	plt.figure(figsize=(12,4))
	plt.scatter(np.arange(np.count_nonzero(idx)),
	            100 * D.leader[idx] / D.ballots_valid_invalid[idx],
	            s=D.voters_registered[idx] / np.quantile(D.voters_registered, 0.5) * 20,
	            alpha=0.5)
	plt.title(election_data.translit(region) + '\n', size=20)

	plt.xlabel('Precinct')
	for x in tsum:
		plt.axvline(x, 0, 1, color='black', alpha=0.25, linewidth=1)
	ax1 = plt.gca()
	ax1.set_xlim((0, np.count_nonzero(idx)))
	ax1.set_xlabel('Precinct')
	ax1.set_xticks(tsum[:-1])
	ax1.set_xticklabels(D.precinct[idx][tidx], ha='center', rotation=90)
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
	import sys
	import argparse
	import matplotlib
	matplotlib.use('Agg')
	import election_data

	parser = argparse.ArgumentParser()
	parser.add_argument('--tsv', default='https://github.com/schitaytesami/lab/releases/download/data/2018.tsv.gz', help='Data file to use, in TSV format')
	parser.add_argument('--npz', default=None, help='Data file to use, in NPZ format')
	parser.add_argument('--year', default=2018, type=int, help='Election year to use from NPZ file')
	args = parser.parse_args()

	if args.npz is not None:
		D = election_data.loadnpz(args.npz, args.year)
	else:
		D = election_data.loadtsv(args.tsv)
	try:
		os.mkdir('bubbles')
	except FileExistsError:
		pass
	for region in np.unique(D.region):
		name = election_data.toident(region)
		print(region, file=sys.stderr, flush=True)
		plot(D, region)
		plt.savefig(os.path.join('bubbles', name + '.png'), bbox_inches='tight')
		plt.close()
