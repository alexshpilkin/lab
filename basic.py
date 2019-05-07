import argparse
import json
import urllib.request
import io
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser()
parser.add_argument('--ruelectiondata_json', default = 'https://github.com/schitaytesami/data/releases/download/20180909/lab_20180909.json')
parser.add_argument('--kobak_npz', default = 'https://github.com/schitaytesami/lab/releases/download/data/electionsData.npz')
parser.add_argument('--kobak_weights', default = 'voters', choices = ['voters', 'given', 'leader', 'off'], help = '''  'off'     (counts polling stations);   'voters'  (counts registered voters);  'given'   (counts given ballots);  'leader'  (counts ballots for the leader) ''')
parser.add_argument('--kobak_minsize', default = 0, type = int)
parser.add_argument('--kobak_addnoise', action = 'store_true', help = ' If add U(-0.5,0.5) noise to the nominators (to remove division artifacts)')
parser.add_argument('--seed', default = 1, type = int)
args = parser.parse_args()

json_read = lambda file_path: json.loads((urllib.request.urlopen if file_path.startswith('http') else (lambda p: open(p, 'rb')))(file_path).read().decode('utf-8'))

np.random.seed(args.seed)
#data = json_read(args.ruelectiondata_json)

######################################################################################
# TODO: below is Kobak's code; gradually refactor it to use our json data

def load_data(url = None, year = None, columns = ['leader', 'voters_registered', 'voters_voted', 'ballots_valid_invalid', 'regions'], translate_latin = False, translate_table = ('абвгдеёжзийклмнопрстуфхцчшщъыьэюя', 'abvgdeejzijklmnoprstufhzcss_y_eua')):
  table = np.load(io.BytesIO(urllib.request.urlopen(url).read()))['_' + str(year)]
  T = lambda c, tr = {ord(a): ord(b) for a, b in zip(*translate_table)}: c.replace(' ', '_').replace(',', '').lower().translate(tr)
  flt = lambda colFilter, excludeFilter = []: [col for col in table.dtype.names if any(T(f) in col for f in colFilter) and (not excludeFilter or all(T(f) not in col for f in excludeFilter)) ]
  leader = np.squeeze(table[flt(['ПУТИН', 'Путин', 'Единая Россия', 'ЕДИНАЯ РОССИЯ', 'Медведев'])[0]])
  voters_registered = np.squeeze(table[flt(['Число избирателей, включенных', 'Число избирателей, внесенных'])[0]])
  voters_voted = np.sum(np.vstack([table[c] for c in flt(['бюллетеней, выданных'])]).T, axis=1)
  ballots_valid_invalid = np.sum(np.vstack([table[c] for c in flt(['действительных', 'недействительных'], ['отметок'])]).T, axis=1)
  regions = table['region']
  return np.rec.fromarrays([leader, voters_registered, voters_voted, ballots_valid_invalid, regions], names = columns)

year = 2018

data = load_data(args.kobak_npz, year = year)
locals().update({k : data[k] for k in data.dtype.names})

# Settings used in our papers:
# * AOAS-2016:         binwidth=0.1,  addNoise=False, weights='voters', minSize = 0
# * Significance-2016: binwidth=0.25, addNoise=True,  weights='off'     minSize = 0
# * Significance-2018: binwidth=0.1,  addNoise=True,  weights='off'     minSize = 0

######################################################################################
# histogram projections

binwidth = 0.1         # Bin width (in percentage points)
ind = (ballots_valid_invalid > 0) & (voters_voted < voters_registered) & (voters_registered >= args.kobak_minsize)
edges = np.arange(-binwidth/2, 100+binwidth/2, binwidth)
centers = np.arange(0,100,binwidth)
noise = np.zeros(np.sum(ind)) if not args.kobak_addnoise else np.random.rand(np.sum(ind)) - .5
w = dict(voters = voters_registered, given = voters_voted, leader = leader)[args.kobak_weights][ind] if args.kobak_weights != 'off' else None
h1 = np.histogram(100 * (voters_voted[ind]+noise)/voters_registered[ind],    bins=edges, weights = w)[0]
h2 = np.histogram(100 * (leader[ind]+noise)/ballots_valid_invalid[ind], bins=edges, weights = w)[0]
ylbl = dict(voters = 'Voters', given = 'Ballots given', leader = 'Ballots for leader').get(args.kobak_weights, 'Polling stations')
plt.figure(figsize=(9,6))
plt.subplot(211)
plt.plot(centers, h1, linewidth=1)
plt.xlabel("Turnout (%)")
plt.ylabel(f'{ylbl} in {binwidth}% bins')
plt.xticks(np.arange(0,101,10))
plt.title(f'Russian election {year}')
plt.subplot(212)
plt.plot(centers, h2, linewidth=1)
plt.xlabel("Leader's result (%)")
plt.ylabel(f'{ylbl} in {binwidth}% bins')
plt.xticks(np.arange(0,101,10))
plt.tight_layout()
plt.savefig('basic1.png')
plt.close()

######################################################################################
# histogram 2d

binwidth = 0.5
edges = np.arange(-binwidth/2, 100+binwidth/2, binwidth)
centers = np.arange(0,100,binwidth)
plt.figure(figsize=(3,3))
ind = (ballots_valid_invalid > 0) & (voters_voted < voters_registered) & (voters_registered >= args.kobak_minsize) & np.array(['Зарубеж' not in s and 'за пределами' not in s for s in regions])
h = np.histogram2d(100 * voters_voted[ind]/voters_registered[ind], 100 * leader[ind]/ballots_valid_invalid[ind], bins=edges, weights = voters_registered[ind])[0]
plt.imshow(h.T, vmin=0, vmax=50000, origin='lower', extent=[0,100,0,100], cmap='viridis', interpolation='none')
plt.xticks([])
plt.yticks([])
plt.axis('off')
plt.text(10,85,year, color='w')
plt.tight_layout()
plt.savefig('basic2.png')
plt.close()
