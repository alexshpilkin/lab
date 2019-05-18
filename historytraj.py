#!/usr/bin/env python3

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

import election_data

def plot(title, D, hours_begin = 8.00, hours_end = 20.00):
	turnout = np.vstack([D[n] for n in D.dtype.names if 'turnout_' in n]).T
	turnout = np.hstack([np.zeros_like(turnout[:, :1]), turnout])
	time = [hours_begin] + [float(n.replace('turnout_', '').replace('h', '.')) for n in D.dtype.names if 'turnout_' in n]

	plt.title(title)
	plt.xlabel('Time')
	plt.ylabel('Turnout %')
	plt.gca().add_collection(matplotlib.collections.LineCollection(np.dstack([np.broadcast_to(time, turnout.shape), turnout * 100])))
	plt.xlim([hours_begin - 1, hours_end + 1])
	plt.ylim([0, 100 + 5])
	plt.vlines(time, *plt.ylim())

if __name__ == '__main__':
	import os
	import argparse
	import matplotlib
	matplotlib.use('Agg')

	parser = argparse.ArgumentParser()
	parser.add_argument('data', nargs='?', metavar='DATA', default='https://github.com/schitaytesami/lab/releases/download/data-v2/2018.tsv.gz', help='Data file to use, in TSV, NPY or NPZ format')
	parser.add_argument('--dpi', default=None, type=int, help='Resolution of the output image')
	parser.add_argument('-o', '--output', default='historytraj', help='Output directory')
	args = parser.parse_args()
	
	if not os.path.exists(args.output):
		os.mkdir(args.output)

	D = election_data.load(args.data)

	for region_code in np.unique(D.region_code):
		print(region_code)
		plt.figure(figsize=(12, 4))
		plot(region_code, election_data.filter(D, region_code=region_code))
		plt.savefig(os.path.join(args.output, region_code + '.png'),
		            bbox_inches='tight', dpi=args.dpi)
		plt.close()
