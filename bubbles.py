#!/usr/bin/env python3

import argparse
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os.path

import election_data

def plot(D, region):
	idx = D.region == region
	plt.figure(figsize=(9,6))
	plt.scatter(np.arange(np.count_nonzero(idx)),
	            100 * D.leader[idx] / D.ballots_valid_invalid[idx],
	            s=D.voters_registered[idx] / np.quantile(D.voters_registered, 0.5) * 20,
	            alpha=0.5)
	plt.title(election_data.translit(region))
	plt.xlabel('Precinct')
	plt.xticks([])
	plt.ylabel('Leader’s result')
	plt.ylim(0, 100)

if __name__ == '__main__':
	from sys import stderr

	parser = argparse.ArgumentParser()
	parser.add_argument('--npz', default='https://github.com/schitaytesami/lab/releases/download/data/data.npz')
	parser.add_argument('--year', default=2018, type=int)
	args = parser.parse_args()

	D = election_data.loadnpz(args.npz, args.year)
	try:
		os.mkdir('bubbles')
	except FileExistsError:
		pass
	for region in np.unique(D.region):
		name = election_data.toident(region)
		print(region, file=stderr, flush=True)
		plot(D, region)
		plt.savefig(os.path.join('bubbles', name + '.png'), bbox_inches='tight')
		plt.close()
