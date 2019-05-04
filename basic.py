import argparse
import json
import urllib.request
import io
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt

json_read = lambda file_path: json.loads((urllib.request.urlopen if file_path.startswith('http') else (lambda p: open(p, 'rb')))(file_path).read().decode('utf-8'))

parser = argparse.ArgumentParser()
parser.add_argument('--ruelectiondata_json', default = 'https://github.com/schitaytesami/data/releases/download/20180909/lab_20180909.json')
parser.add_argument('--kobak_npz', default = 'https://github.com/schitaytesami/lab/releases/download/data/electionsData.npz')
parser.add_argument('--seed', default = 1, type = int)
args = parser.parse_args()

np.random.seed(args.seed)
#data = json_read(args.ruelectiondata_json)

# TODO: below is Kobak's code; gradually refactor it to use our json data

# Histograms for one particular year

year     = 2018        # Election year
binwidth = 0.1         # Bin width (in percentage points)
addNoise = False       # If add U(-0.5,0.5) noise to the nominators (to remove division artifacts)
weights  = 'voters'    # Weights: can be 'off'     (counts polling stations), 
                       #                 'voters'  (counts registered voters),
                       #                 'given'   (counts given ballots)
                       #                 'leader'  (counts ballots for the leader)
minSize  = 0           # Exclude polling stations with number of voters less than minSize

# Settings used in our papers:
# * AOAS-2016:         binwidth=0.1,  addNoise=False, weights='voters', minSize = 0
# * Significance-2016: binwidth=0.25, addNoise=True,  weights='off'     minSize = 0
# * Significance-2018: binwidth=0.1,  addNoise=True,  weights='off'     minSize = 0

######################################################################################
npz = np.load(io.BytesIO(urllib.request.urlopen(args.kobak_npz).read()))
C = lambda c, tr = {ord(a): ord(b) for a, b in zip(u'абвгдеёжзийклмнопрстуфхцчшщъыьэюя',u'abvgdeejzijklmnoprstufhzcss_y_eua')}: c.replace(' ', '_').replace(',', '').lower().translate(tr)
loaded = {}
for year in [2000, 2003, 2004, 2007, 2008, 2011, 2012, 2016, 2018]:
	table = npz['_' + str(year)]
	table_columns = table.dtype.names
	colFilter = ['ПУТИН', 'Путин', 'Единая Россия', 'ЕДИНАЯ РОССИЯ', 'Медведев']
	col = [col for col in table_columns if any([C(f) in col for f in colFilter])]
	leader = np.squeeze(table[col[0]])
	colFilter = ['Число избирателей, включенных', 'Число избирателей, внесенных']
	col = [col for col in table_columns if any([C(f) in col for f in colFilter])]
	voters = np.squeeze(table[col[0]])
	colFilter = ['бюллетеней, выданных']                # should select 3 columns
	col = [col for col in table_columns if any([C(f) in col for f in colFilter])]
	given = np.sum(np.vstack([table[c] for c in col]).T, axis=1)
	colFilter = ['действительных', 'недействительных']  # should select 2 columns
	excludeFilter = ['отметок']  # excludes one additional column in the 2000 data
	col = [col for col in table_columns if any([C(f) in col for f in colFilter]) and 
										   all([C(f) not in col for f in excludeFilter])]
	received = np.sum(np.vstack([table[c] for c in col]).T, axis=1)
	regions = table['region']
	tiks = table['tik']
	uiks = table['uik']
	loaded[year] = (voters, given, received, leader, regions, tiks, uiks)
loaddata = loaded.get

voters, given, received, leader = loaddata(year)[:4]

ind = (received > 0) & (given < voters) & (voters >= minSize)
edges = np.arange(-binwidth/2, 100+binwidth/2, binwidth)
centers = np.arange(0,100,binwidth)

noise = np.zeros(np.sum(ind)) if not addNoise else np.random.rand(np.sum(ind)) - .5

w = None
if weights == 'voters': w = voters[ind]
if weights == 'given':  w = given[ind]
if weights == 'leader': w = leader[ind]
h1 = np.histogram(100 * (given[ind]+noise)/voters[ind],    bins=edges, weights = w)[0]
h2 = np.histogram(100 * (leader[ind]+noise)/received[ind], bins=edges, weights = w)[0]

ylbl = 'Polling stations'
if weights == 'voters': ylbl = 'Voters'
if weights == 'given':  ylbl = 'Ballots given'
if weights == 'leader': ylbl = 'Ballots for leader'

plt.figure(figsize=(9,6))
plt.subplot(211)
plt.plot(centers, h1, linewidth=1)
plt.xlabel("Turnout (%)")
plt.ylabel('{} in {}% bins'.format(ylbl, binwidth))
plt.xticks(np.arange(0,101,10))
plt.title('Russian election {}'.format(year))

plt.subplot(212)
plt.plot(centers, h2, linewidth=1)
plt.xlabel("Leader's result (%)")
plt.ylabel('{} in {}% bins'.format(ylbl, binwidth))
plt.xticks(np.arange(0,101,10))
plt.tight_layout()

plt.savefig('basic1.png')
plt.close()

# 2D histograms for all years

years = [2000, 2003, 2004, 2007, 2008, 2011, 2012, 2016, 2018]
binwidth = 0.5
minSize = 0

edges = np.arange(-binwidth/2, 100+binwidth/2, binwidth)
centers = np.arange(0,100,binwidth)

plt.figure(figsize=(9,9))
for i,y in enumerate(years):
    voters, given, received, leader, regions, tiks = loaddata(y)[:6]

    plt.subplot(3, 3, i+1)
    ind = (received > 0) & (given < voters) & (voters >= minSize) & np.array(['Зарубеж' not in s and 'за пределами' not in s for s in regions])
    h = np.histogram2d(100 * given[ind]/voters[ind], 100 * leader[ind]/received[ind], 
                       bins=edges, weights = voters[ind])[0]
    plt.imshow(h.T, vmin=0, vmax=50000, origin='lower', extent=[0,100,0,100], 
               cmap=plt.get_cmap('viridis'), interpolation='none')
    plt.xticks([])
    plt.yticks([])
    plt.axis('off')
    plt.text(10,85,y, color='w')

plt.tight_layout()
plt.savefig('basic2.png')
plt.close()
