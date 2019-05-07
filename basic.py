#!/usr/bin/env python3

import argparse
import json
import urllib.request
import io
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser()
parser.add_argument('--ruelectiondata_json', default='https://github.com/schitaytesami/data/releases/download/20180909/lab_20180909.json')
parser.add_argument('--kobak_npz', default='https://github.com/schitaytesami/lab/releases/download/data/electionsData.npz')
parser.add_argument('--weights', default='voters', choices=['voters', 'given', 'leader', 'off'], help='''  'off'     (counts polling stations);   'voters'  (counts registered voters);  'given'   (counts given ballots);  'leader'  (counts ballots for the leader) ''')
parser.add_argument('--kobak_minsize', default=0, type=int)
parser.add_argument('--kobak_addnoise', action='store_true', help='Whether to add add U(-0.5,0.5) noise to the numerators (to remove division artifacts)')
parser.add_argument('--seed', default=1, type=int)
parser.add_argument('--colormap', default='viridis', type=str)
args = parser.parse_args()

json_read = lambda file_path: json.loads((urllib.request.urlopen if file_path.startswith('http') else (lambda p: open(p, 'rb')))(file_path).read().decode('utf-8'))
np_read = lambda file_path: np.load(io.BytesIO((urllib.request.urlopen if file_path.startswith('http') else (lambda p: open(p, 'rb')))(file_path).read()))

np.random.seed(args.seed)
#data = json_read(args.ruelectiondata_json)

######################################################################################
# TODO: below is Kobak's code; gradually refactor it to use our json data

def load_data(url=None, year=None, columns=['leader', 'voters_registered', 'voters_voted', 'ballots_valid_invalid', 'regions'], translate_latin=False, translate_table=('абвгдеёжзийклмнопрстуфхцчшщъыьэюя', 'abvgdeejzijklmnoprstufhzcss_y_eua')):
  table = np_read(url)['_' + str(year)]
  T = lambda c, tr = {ord(a): ord(b) for a, b in zip(*translate_table)}: c.replace(' ', '_').replace(',', '').lower().translate(tr)
  flt = lambda colFilter, excludeFilter=[]: \
        [col for col in table.dtype.names if any(T(f) in col for f in colFilter) and
                                             (not excludeFilter or all(T(f) not in col for f in excludeFilter))]
  leader = np.squeeze(table[flt(['ПУТИН', 'Путин', 'Единая Россия', 'ЕДИНАЯ РОССИЯ', 'Медведев'])[0]])
  voters_registered = np.squeeze(table[flt(['Число избирателей, включенных', 'Число избирателей, внесенных'])[0]])
  voters_voted = np.sum(np.vstack([table[c] for c in flt(['бюллетеней, выданных'])]).T, axis=1)
  ballots_valid_invalid = np.sum(np.vstack([table[c] for c in flt(['действительных', 'недействительных'], ['отметок'])]).T, axis=1)
  regions = table['region']
  return np.rec.fromarrays([leader, voters_registered, voters_voted, ballots_valid_invalid, regions], names=columns)

year = 2018

D = load_data(args.kobak_npz, year=year)
locals().update({k : D[k] for k in D.dtype.names})

wval, wlbl = {
  'voters': (voters_registered, 'Voters'),
  'given':  (voters_voted, 'Ballots given'),
  'leader': (leader, 'Ballots for leader'),
  'off':    (np.ones(voters_registered.shape), 'Polling stations'),
}.get(args.weights, None)

# Settings used in our papers:
# * AOAS-2016:         binwidth=0.1,  addNoise=False, weights='voters', minSize = 0
# * Significance-2016: binwidth=0.25, addNoise=True,  weights='off'     minSize = 0
# * Significance-2018: binwidth=0.1,  addNoise=True,  weights='off'     minSize = 0

fig, axs = plt.subplots(2, 2, sharex='col', sharey='row', figsize=[9,9], gridspec_kw={'width_ratios': [3,1], 'wspace': 0.2, 'height_ratios': [1,3], 'hspace': 0.2})
fig.suptitle(f'Russian election {year}', size=24, y=0.925, va='baseline')

######################################################################################
# histogram projections

binwidth = 0.1         # Bin width (in percentage points)
ind = (ballots_valid_invalid > 0) & (voters_voted < voters_registered) & (voters_registered >= args.kobak_minsize)
edges = np.arange(-binwidth/2, 100 + binwidth/2, binwidth)
centers = np.arange(0, 100, binwidth)
noise = np.zeros(np.sum(ind)) if not args.kobak_addnoise else np.random.rand(np.sum(ind)) - .5
w = wval[ind]
h1 = np.histogram(100 * (voters_voted[ind] + noise) / voters_registered[ind], bins=edges, weights=w)[0]
h2 = np.histogram(100 * (leader[ind] + noise) / ballots_valid_invalid[ind], bins=edges, weights=w)[0]

axs[0,0].plot(centers, h1, linewidth=1, color=plt.get_cmap(args.colormap)(0))
axs[0,0].axis('off')

axs[1,1].plot(h2, centers, linewidth=1, color=plt.get_cmap(args.colormap)(0))
axs[1,1].axis('off')

######################################################################################
# histogram 2d

binwidth = 0.5
edges = np.arange(-binwidth/2, 100 + binwidth/2, binwidth)
centers = np.arange(0, 100, binwidth)

ind = (ballots_valid_invalid > 0) & (voters_voted < voters_registered) & (voters_registered >= args.kobak_minsize) & np.array(['Зарубеж' not in s and 'за пределами' not in s for s in regions])
h = np.histogram2d(100 * voters_voted[ind] / voters_registered[ind], 100 * leader[ind] / ballots_valid_invalid[ind], bins=edges, weights=wval[ind])[0]

axs[1,0].imshow(h.T, vmin=0, vmax=np.quantile(h, 0.99), origin='lower', extent=[0,100,0,100], cmap=args.colormap, interpolation='none')
axs[1,0].axis('off')
plt.text(10, 85, year, color='w')

fig.delaxes(axs[0,1])

plt.savefig('basic.png', bbox_inches='tight')
plt.close()
