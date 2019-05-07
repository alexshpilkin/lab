#!/usr/bin/env python3

import argparse
import json
import urllib.request
import io
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.transforms as xfrm

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

# Settings used in our papers:
# * AOAS-2016:         binwidth=0.1,  addNoise=False, weights='voters', minSize = 0
# * Significance-2016: binwidth=0.25, addNoise=True,  weights='off'     minSize = 0
# * Significance-2018: binwidth=0.1,  addNoise=True,  weights='off'     minSize = 0

binwidth = 0.1
edges = np.arange(-binwidth/2, 100 + binwidth/2, binwidth)
centers = np.arange(0, 100, binwidth)

wval, wlbl = {
  'voters': (voters_registered, 'voters registered'),
  'given':  (voters_voted, 'ballots given'),
  'leader': (leader, 'ballots for leader'),
  'off':    (np.ones(voters_registered.shape), 'polling stations'),
}.get(args.weights, None)
ind = (ballots_valid_invalid > 0) & (voters_voted < voters_registered) & (voters_registered >= args.kobak_minsize) & np.array(['Зарубеж' not in s and 'за пределами' not in s for s in regions])
noise = np.zeros(np.sum(ind)) if not args.kobak_addnoise else np.random.rand(np.sum(ind)) - .5
h = np.histogram2d(100 * (voters_voted[ind] + noise) / voters_registered[ind], 100 * (leader[ind] + noise) / ballots_valid_invalid[ind], bins=edges, weights=wval[ind])[0]
ht = np.sum(h, axis=1)
hr = np.sum(h, axis=0)

ymax = min(np.max(ht), np.max(hr))
ylog, yfac = 0, 1
while yfac < ymax:
  ylog, yfac = ylog+1, yfac*10
ylog, yfac = ylog-1, yfac//10

size, aspect, spacing = 9.0, 3, 0.15

fig, axs = plt.subplots(2, 2, sharex='col', sharey='row', figsize=[size, size], gridspec_kw=dict(width_ratios=[aspect, 1], wspace=spacing, height_ratios=[1, aspect], hspace=spacing))
fig.suptitle(f'Russian election {year}', size=20, y=0.925, va='baseline')

ax = axs[0,1]
ax.text(0.5, 0.5, f'$\\times 10^{{{ylog}}}$ {wlbl}\nin ${binwidth}\\,\\%$ bin', wrap=True, ha='center', va='center', transform=ax.transAxes)  # the \n is a hack to force good wrapping
ax.set_frame_on(False)
ax.axhline(0, 0, 1, color='black')
ax.axvline(0, 0, 1, color='black')
ax.tick_params(right=False, top=False, left=True, bottom=True,
               labelright=False, labeltop=False, labelleft=True, labelbottom=True)

ax = axs[0,0]
ax.plot(centers, ht / yfac, linewidth=1, color=plt.get_cmap(args.colormap)(0))
ax.set_xticks(np.arange(0, 101, 10))
ax.set_ylim(0, ax.get_ylim()[1])
ax.set_frame_on(False)
ax.axhline(0, 0, 1, color='black')
ax.axvline(100, 0, 1, color='black')
ax.tick_params(right=True, top=False, left=False, bottom=True,
               labelright=False, labeltop=False, labelleft=False, labelbottom=True)

ax = axs[1,1]
ax.plot(hr / yfac, centers, linewidth=1, color=plt.get_cmap(args.colormap)(0))
ax.set_xlim(0, ax.get_xlim()[1])
ax.set_yticks(np.arange(0, 101, 10))
ax.set_frame_on(False)
ax.axhline(100, 0, 1, color='black')
ax.axvline(0, 0, 1, color='black')
ax.tick_params(right=False, top=True, left=True, bottom=False,
               labelright=False, labeltop=False, labelleft=True, labelbottom=False)

ax = axs[1,0]
ax.imshow(h.T, vmin=0, vmax=np.quantile(h, 0.99), origin='lower', extent=[0,100,0,100], cmap=args.colormap, interpolation='none')
ax.set_xlabel('Turnout %')
ax.set_ylabel('Leader’s result %')
ax.set_frame_on(False)
ax.axhline(100, 0, 1, color='black')
ax.axvline(100, 0, 1, color='black')
ax.tick_params(right=True, top=True, left=False, bottom=False,
               labelright=False, labeltop=False, labelleft=False, labelbottom=False)

top    = min(axs[0,0].get_position().y0, axs[0,0].get_position().y1)
bottom = max(axs[1,0].get_position().y0, axs[1,0].get_position().y1)
offset = ((top - bottom) / axs[0,0].get_position().height / 2 -
          axs[0,0].xaxis.get_major_ticks()[0].get_tick_padding() / 144)
for tick in axs[0,0].xaxis.get_major_ticks() + axs[0,1].xaxis.get_major_ticks():
  tick.label1.set_va('center')
  tick.set_pad(0)
  tick.label1.set_position((tick.label1.get_position()[0], -offset))

right = min(axs[1,1].get_position().x0, axs[1,1].get_position().x1)
left  = max(axs[1,0].get_position().x0, axs[1,0].get_position().x1)
offset = ((right - left) / axs[1,1].get_position().width / 2 -
          axs[1,1].yaxis.get_major_ticks()[0].get_tick_padding() / 144)
for tick in axs[0,1].yaxis.get_major_ticks() + axs[1,1].yaxis.get_major_ticks():
  tick.label1.set_ha('center')
  tick.set_pad(0)
  tick.label1.set_position((-offset, tick.label1.get_position()[1]))

plt.savefig('basic.png', bbox_inches='tight')
plt.close()
