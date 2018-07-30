from PIL import Image
import numpy as np
from tessellate_fast import tessel_fast
from tessellate_lowmem import tessel_low_mem
from InverseTransformSampling import transformp,gaussian
import argparse

# Parse command line arguments
parser = argparse.ArgumentParser()
parser.add_argument('input',help='Input Image file')
parser.add_argument('output',help='Output Image file')
parser.add_argument('cn',default=0,help='Number of clusters (default = 0.1*size)',type=int)
parser.add_argument('--rescale',default = 1,help='Rescaling factor for large images',type=float)
parser.add_argument('--border',default=0,help='Make border [1/0]?',type=int)
parser.add_argument('--method',default='low_mem',help='fast vs low_mem methods. Default is low_mem.')
parser.add_argument('--threshold',default=200,help='Only for borders. Threshold distance.',type=float)
parser.add_argument('--clusmap',default=0,help='Load a specific cluster map as tab-separated text file')
parser.add_argument('--probmap',default=0,help='Load a 2D probability map for cluster generation')
parser.add_argument('--channel',default=0,help='Whether to tessellate along only R,G,B or combinations?',choices=['r','g','b','rand','rb','rg','bg','randdual'])
parser.add_argument('--verbose',default=1,help='Print progress?[1/0]',type=int)
parser.add_argument('--seed',default='None',help='Seed for PRNG')
parser.add_argument('--gaussianvars',nargs='*',help='Only for gaussian probmap (mx,my,sigmax,sigmay,corr(opt),spacing(opt))')
args = parser.parse_args()

# seed
if not args.seed=='None':
    np.random.seed(int(args.seed))

# load and rescale input image
img = Image.open(args.input)
img = img.resize((int(img.size[0]/args.rescale),int(img.size[1]/args.rescale)))
img = np.array(img)
if args.cn==0:
    args.cn = int(np.mean(img.shape)*0.1)

# verbose mode?
verb = [False,True][args.verbose]


if verb:
    print('Making Clusters.')
# Cluster generation
if not (args.clusmap == 0): # Pre-formed cluster-map
    clusters = []
    with open(args.clusmap) as f:
        for row in f:
            clusters.append(list(map(float,row.split('\t'))))
elif not (args.probmap == 0): #Probability distribution for Inverse Transform Sampling
    if args.probmap == 'gaussian':
        if len(args.gaussianvars)<6:
            defs = [0.5,0.5,100,100,0,None]
            args.gaussianvars = list(map(float,args.gaussianvars)) + defs[len(args.gaussianvars):len(defs)]
        arguments = args.gaussianvars+[img.shape]
        g = gaussian(*arguments)
        clusters = transformp(args.cn,g[0],g[1],g[2],img.shape)
        clusters = np.array(tuple(clusters))
else:
    clusters = np.array(tuple(zip(np.random.rand(args.cn)*img.shape[0],np.random.rand(args.cn)*img.shape[1])))

if verb:
    print('Done.')
    print('Making Voronoi Tessellations....')

# Tessellating
if args.method=='fast':
    dist = tessel_fast(clusters,img.shape,[False,True][args.verbose],[False,True][args.border],args.threshold)
elif args.method=='low_mem':
    dist = tessel_low_mem(clusters,img.shape,[False,True][args.verbose],[False,True][args.border],args.threshold)
else:
    print("ERROR: Invalid Method")
    quit(1)

if verb:
    print('\t\t\t\t\t\nDone.')
# Averaging over Voronoi clusters
s = set(dist.flatten())
sl = len(s)
x=0 # counter for Verbose mode
if verb:
    print('\nAveraging over Voronoi clusters.')
for i in (set(list(range(args.cn))) & s):
    if verb:
        print(str(int(x/sl*100))+'% done \t\t\r',end='')
        x += 1
    if args.channel in ['r','g','b']:
        chn = {'r':0,'g':1,'b':2}[args.channel]
        img[dist == i, chn] = int(np.mean(img[dist == i, chn].flatten()))
        continue
    elif args.channel=='rand':
        chn = np.random.randint(0,3)
        img[dist == i, chn] = int(np.mean(img[dist == i, chn].flatten()))
        continue
    elif args.channel=='randdual':
        chn1 = np.random.randint(0,3)
        chn2 = np.random.randint(0,3)
        img[dist == i, chn1],img[dist == i, chn2] = (np.array(img[dist == i, chn2],copy=True),np.array(img[dist == i, chn1],copy=True))
        continue
    elif args.channel in ['rb','rg','gb']:
        perms = ['rb','rg','gb']
        chn1,chn2 = [(0,2),(0,1),(1,2)][perms.index(args.channel)]
        chn1,chn2 = [(chn1,chn2),(0,0)][np.random.randint(0,2)]
        if chn1==chn2:
            continue
        img[dist == i, chn1],img[dist == i, chn2] = (np.array(img[dist == i, chn2],copy=True),np.array(img[dist == i, chn1],copy=True))
        continue
    img[dist==i,0]=int(np.mean(img[dist==i,0].flatten()))
    img[dist==i,1]=int(np.mean(img[dist==i,1].flatten()))
    img[dist==i,2]=int(np.mean(img[dist==i,2].flatten()))
if [False,True][args.border]:
    img[dist==args.cn+1,0]=0
    img[dist==args.cn+1,1]=0
    img[dist==args.cn+1,2]=0

if verb:
    print('\t\t\t\t\t\nDone.')
    print('Saving Output file.')
img = Image.fromarray(img)
img.save(args.output)