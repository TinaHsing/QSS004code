import numpy as np 
import matplotlib.pyplot as plt
from scipy.signal import find_peaks

fp = open('mix1.txt','r')
temp = [line.rstrip('\n') for line in fp]

datax =[]
datay=[]
for a in temp:
	b = a.split(',')
	datax.append(float(int(b[0])))
	datay.append(float(b[1]))

peaks, _= find_peaks(datay, height = -35, prominence = (5, None))
print peaks
plt.plot(datay)

plt.show()

