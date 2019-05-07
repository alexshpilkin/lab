#!/usr/bin/env python3

import argparse
import json
import io
import re
import urllib.request
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser()
parser.add_argument('--npz', default='https://github.com/schitaytesami/lab/releases/download/data/electionsData.npz')
parser.add_argument('--weights', default='voters', choices={'voters', 'given', 'leader', 'ones'}, help='''  'ones'    (counts polling stations);   'voters'  (counts registered voters);  'given'   (counts given ballots);  'leader'  (counts ballots for the leader) ''')
parser.add_argument('--min-size', default=0, type=int)
parser.add_argument('--noise', action='store_true', help='Add U(-0.5,0.5) noise to the numerators (to remove division artifacts)')
parser.add_argument('--bin-width', default=0.25, type=float, help='Bin width in percentage points')
parser.add_argument('--seed', default=1, type=int, help='Seed for random noise')
parser.add_argument('--colormap', default='viridis', type=str)
parser.add_argument('--dpi', default=None, type=int)
args = parser.parse_args()

def urlopen(url):
  if re.fullmatch(r'[A-Za-z0-9.+-]+://.*', url):  # RFC 3986
    return urllib.request.urlopen(url)
  else:
    return open(url, 'rb')

np.random.seed(args.seed)

######################################################################################

TRANSLIT = ('абвгдеёжзийклмнопрстуфхцчшщъыьэюя',
            'abvgdeejzijklmnoprstufhzcss_y_eua')
TRANSLIT = {ord(a): ord(b) for a, b in zip(*TRANSLIT)}
COLUMNS = ('leader', 'voters_registered', 'voters_voted', 'ballots_valid_invalid', 'regions')

def translit(s):
  return s.translate(TRANSLIT)
def toident(s):
  return translit(s.lower()).replace(' ', '_').replace(',', '')

def loadnpz(url, year):
  with urlopen(url) as file:
    table = np.load(file)['_' + str(year)]

  def flt(include, exclude=()):
    return [col
            for col in table.dtype.names
            if any(toident(f) in col for f in include) and
               all(toident(f) not in col for f in exclude)]

  leader = np.squeeze(table[flt({'Путин', 'Единая Россия', 'Медведев'})[0]])
  voters_registered = np.squeeze(table[flt({'Число избирателей, включенных', 'Число избирателей, внесенных'})[0]])
  voters_voted = np.sum(np.vstack([table[c] for c in flt({'бюллетеней, выданных'})]).T, axis=1)
  ballots_valid_invalid = np.sum(np.vstack([table[c] for c in flt({'действительных', 'недействительных'}, {'отметок'})]).T, axis=1)
  regions = table['region']
  return np.rec.fromarrays([leader, voters_registered, voters_voted, ballots_valid_invalid, regions], names=COLUMNS)

# Settings used in our papers:
# * AOAS-2016:         binwidth=0.1,  addNoise=False, weights='voters', minsize = 0
# * Significance-2016: binwidth=0.25, addNoise=True,  weights='ones',   minsize = 0
# * Significance-2018: binwidth=0.1,  addNoise=True,  weights='ones',   minsize = 0

def histogram(data, binwidth, weights='voters', minsize=0, noise=False):
  edges = np.arange(-binwidth/2, 100 + binwidth/2, binwidth)
  centers = np.arange(0, 100, binwidth)

  wval, wlbl = {
    'voters': (data.voters_registered, 'voters registered'),
    'given':  (data.voters_voted, 'ballots given'),
    'leader': (data.leader, 'ballots for leader'),
    'ones':   (np.ones(data.voters_registered.shape), 'polling stations'),
  }.get(weights)
  ind = (data.ballots_valid_invalid > 0) & (data.voters_voted < data.voters_registered) & (data.voters_registered >= minsize) & np.array(['Зарубеж' not in s and 'за пределами' not in s for s in data.regions])
  noise1 = np.zeros(np.sum(ind)) if not noise else np.random.rand(np.sum(ind)) - .5
  noise2 = np.zeros(np.sum(ind)) if not noise else np.random.rand(np.sum(ind)) - .5
  h = np.histogram2d(100 * (data.voters_voted[ind] + noise1) / data.voters_registered[ind],
                     100 * (data.leader[ind] + noise2) / data.ballots_valid_invalid[ind],
                     bins=edges, weights=wval[ind])[0]
  return wlbl, centers, h

def plot(title, wlbl, centers, h, cmap='viridis'):
  binwidth=centers[1] - centers[0]
  ht = np.sum(h, axis=1)
  hr = np.sum(h, axis=0)

  ymax = min(np.max(ht), np.max(hr))
  ylog, yfac = 0, 1
  while yfac < ymax:
    ylog, yfac = ylog+1, yfac*10
  ylog, yfac = ylog-1, yfac//10

  size, aspect, spacing = 9.0, 3, 0.15

  fig, axs = plt.subplots(2, 2, sharex='col', sharey='row', figsize=[size, size], gridspec_kw=dict(width_ratios=[aspect, 1], wspace=spacing, height_ratios=[1, aspect], hspace=spacing))
  fig.suptitle(title, size=20, y=0.925, va='baseline')

  ax = axs[0,1]
  ax.text(0.5, 0.5, f'$\\times 10^{{{ylog}}}$ {wlbl}\nin ${binwidth}\\,\\%$ bin', wrap=True, ha='center', va='center', transform=ax.transAxes)  # the \n is a hack to force good wrapping
  ax.set_frame_on(False)
  ax.axhline(0, 0, 1, color='black')
  ax.axvline(0, 0, 1, color='black')
  ax.tick_params(right=False, top=False, left=True, bottom=True,
                 labelright=False, labeltop=False, labelleft=True, labelbottom=True)

  ax = axs[0,0]
  ax.plot(centers, ht / yfac, linewidth=1, color=plt.get_cmap(cmap)(0))
  ax.set_xticks(np.arange(0, 101, 10))
  ax.set_ylim(0, ax.get_ylim()[1])
  ax.set_frame_on(False)
  ax.axhline(0, 0, 1, color='black')
  ax.axvline(100, 0, 1, color='black')
  ax.tick_params(right=True, top=False, left=False, bottom=True,
                 labelright=False, labeltop=False, labelleft=False, labelbottom=True)

  ax = axs[1,1]
  ax.plot(hr / yfac, centers, linewidth=1, color=plt.get_cmap(cmap)(0))
  ax.set_xlim(0, ax.get_xlim()[1])
  ax.set_yticks(np.arange(0, 101, 10))
  ax.set_frame_on(False)
  ax.axhline(100, 0, 1, color='black')
  ax.axvline(0, 0, 1, color='black')
  ax.tick_params(right=False, top=True, left=True, bottom=False,
                 labelright=False, labeltop=False, labelleft=True, labelbottom=False)

  ax = axs[1,0]
  ax.imshow(h.T, vmin=0, vmax=np.quantile(h, 0.99), origin='lower', extent=[0,100,0,100], cmap=cmap, interpolation='none')
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

year = 2018
D = loadnpz(args.npz, year)
wlbl, centers, h = histogram(D, args.bin_width, weights=args.weights, minsize=args.min_size, noise=args.noise)
plot(f'Russian election {year}', wlbl, centers, h, cmap=args.colormap)
plt.savefig('basic.png', bbox_inches='tight', dpi=args.dpi)
plt.close()
