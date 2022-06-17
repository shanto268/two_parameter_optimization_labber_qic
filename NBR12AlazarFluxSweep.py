# -*- coding: utf-8 -*-

# from VISAdrivers.continuousAlazar import ADC
# from tools.datatools import bin2csv
# import numpy as np
import os
# import matplotlib.pyplot as plt
# from matplotlib.colors import LogNorm
# from scipy.signal import windows, convolve
import time
import Labber
import subprocess
import numpy as np
import fitTools.quasiparticleFunctions as qp
import matplotlib.pyplot as plt
import matplotlib.colors as mplc

pathToExe = r'C:/Users/LFL/lflPython/AlazarDrivers/CS_Average/x64/Release/ATS9371_CS_Average.exe'

client = Labber.connectToServer()
# LO = client.connectToInstrument('Rohde&Schwarz RF Source',
#                                 dict(interface='TCPIP',address='192.168.1.128'))
# LO.startInstrument()
SMU = client.connectToInstrument('Keithley 2400 SourceMeter',dict(interface='GPIB',address='23'))
SMU.startInstrument()

#nHours = 12
#nMinutesDelay = 30
#numberTraces = nHours*60//nMinutesDelay
numberTraces = 1
acquisitionLength_sec = 1
origRateMHz = 500
# avgTime = 3e-6
sampleRateMHz = 10 # Note this should always be a integer factor of origRateMHz. Such as 15 x 20 = 300.
DAsetting = 10
LOfrequency = 5.5806 # GHz
T = 29

# LO.setValue('Frequency',LOfrequency*1e9)

lI = np.arange(-0.8e-3,-1.2e-3,-0.005e-3)
x = []
y = []
for I in lI:
    SMU.setValue('Source current',I)
    
    
    
    StringForFlux = r'{}GHz_DA{}_SR{}MHz'.format(LOfrequency,DAsetting,sampleRateMHz)
    path = r"G:\Shared drives\LFL\Projects\Quasiparticles\NBR19_Jun13_2022\fluxSweep\{}\\".format(StringForFlux)
    figpath = r"G:\Shared drives\LFL\Projects\Quasiparticles\NBR19_Jun13_2022\fluxSweep\Figures\\"
    
    if not os.path.exists(path):
        os.makedirs(path)
    if not os.path.exists(figpath):
        os.makedirs(figpath)
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    savefile = path + 'NBR19_{}.bin'.format(timestamp)
    
    samplesPerPoint = int(max(origRateMHz/sampleRateMHz,1))
    actualSampleRateMHz = origRateMHz/samplesPerPoint
    
    # write metadata to corresponding .txt file
    with open(savefile[0:-4] + ".txt",'w') as f:
        from time import strftime
        f.write(strftime("%c")+'\n')
        f.write("Channels: " + 'AB' + '\n')
        f.write("Acquisition duration: " + str(acquisitionLength_sec) + " seconds." + '\n')
        f.write("Sample Rate MHz: " + str(actualSampleRateMHz) + '\n')
        f.write("LO frequency: "+str(LOfrequency) + " GHz")
        f.write("flux bias: "+str(I) + " A")
        f.write("DA setting: "+str(DAsetting) + " dB\n")
        f.write("Temperature: "+str(T)+' mK\n')
        f.write("Victor current: "+str(I*1000)+' mA\n')
    
    
    Creturn = subprocess.getoutput('"{}" {} {} "{}"'.format(pathToExe,int(acquisitionLength_sec),samplesPerPoint,savefile))
    
    print(Creturn)
    
    data = qp.loadAlazarData(savefile)
    data = qp.BoxcarDownsample(data,2e-6,10e6)
    data = qp.uint16_to_mV(data)
    # ax = qp.plotComplexHist(data[0],data[1])
    # ax.set_title(f'{I*1e3:.1f} mA')
    # plt.savefig(figpath+f'\\{I*1e6}uA.png')
    # plt.show();
    # plt.close();
    x.append(np.mean(data[0]))
    y.append(np.mean(data[1]))
    
    fig,ax = plt.subplots()
    # hi = plt.hist2d(data[0],data[1],bins=(80,80),cmap=plt.get_cmap('Greys'))
    ax,hi = qp.plotComplexHist(data[0],data[1],returnHistData=True)
    # hi = np.histogram2d(data[0],data[1],bins=(200,200))
    xc = (hi[1][:-1]+hi[1][1:])/2
    yc = (hi[2][:-1]+hi[2][1:])/2
    # guess = [60000,np.mean(data[0]),np.mean(data[1]),1,1,0]
    # xx,yy,amps,means,varis = qp.fitGaussian(hi,guess)
    # # f = gaussianMix(heights,widths,means)
    # qp.make_ellipses2(means,varis,ax,['red'])
    ax.set_title(f'{I*1e3:.1f} mA')
    plt.savefig(figpath+f'\\{I*1e6}uA.png')
    plt.show()
    plt.close()
    # print(varis)

fig,ax = plt.subplots(1,1,'none',figsize=[4,3],constrained_layout=True)
colors = plt.get_cmap('gist_rainbow', len(x))
norm = mplc.Normalize(vmin=0, vmax=len(x))
sm = plt.cm.ScalarMappable(cmap=colors, norm=norm)
sm.set_array([])
fig.colorbar(sm, aspect=60)
plt.plot(x,y)
for i,(xx,yy) in enumerate(zip(x,y)):
    plt.scatter(xx,yy,c=colors(i))
plt.savefig(figpath+r'summary.png')
# LO.setValue('Frequency',LOfrequency*1e9)

# stringdesc = f"{int(LOfrequency*1000)}"


# # StringForFlux = r'{}GHz_DA{}_SR{}MHz'.format(LOfrequency,DAsetting,sampleRateMHz)
# path = r"G:\Shared drives\LFL\Projects\Quasiparticles\TestOffsetNoise\\"
# figpath = r"G:\Shared drives\LFL\Projects\Quasiparticles\TestOffsetNoise\figures\\"

# if not os.path.exists(path):
#     os.makedirs(path)
# if not os.path.exists(figpath):
#     os.makedirs(figpath)

# timestamp = time.strftime("%Y%m%d_%H%M%S")
# savefile = path + '{}.bin'.format(stringdesc)

# samplesPerPoint = int(max(origRateMHz/sampleRateMHz,1))
# actualSampleRateMHz = origRateMHz/samplesPerPoint

# # write metadata to corresponding .txt file
# with open(savefile[0:-4] + ".txt",'w') as f:
#     from time import strftime
#     f.write(strftime("%c")+'\n')
#     f.write("Channels: " + 'AB' + '\n')
#     f.write("Acquisition duration: " + str(acquisitionLength_sec) + " seconds." + '\n')
#     f.write("Sample Rate MHz: " + str(actualSampleRateMHz) + '\n')
#     f.write("LO frequency: "+str(LOfrequency) + " GHz")

# # savefile = adc.startTriggeredCapture(acquisitionLength_sec,channel='AB',dataFilePath=savefile,returnfname=True,downsamplerate=sampleRateMHz*1e6)
# Creturn = subprocess.getoutput('"{}" {} {} "{}"'.format(pathToExe,int(acquisitionLength_sec),samplesPerPoint,savefile))

# print(Creturn)

# data = qp.loadAlazarData(savefile)
# data = qp.BoxcarDownsample(data,2e-6,sampleRateMHz*1e6)
# data = qp.uint16_to_mV(data)
# ax,hi = qp.plotComplexHist(data[0],data[1],bins=(80,80),returnHistData=True)
# xc = (hi[1][:-1]+hi[1][1:])/2
# yc = (hi[2][:-1]+hi[2][1:])/2
# guess = [1000,0,0,1,1,0]
# xx,yy,amps,means,varis = qp.fitGaussian(hi,guess)
# # f = gaussianMix(heights,widths,means)
# qp.make_ellipses2(means,varis,ax,['red'])
# print(f'\n\n{stringdesc} gives {varis}\n\n')
# plt.title(f'{stringdesc}')
# plt.savefig(figpath+f'{stringdesc}_IQhist.png')
# plt.show()




# adc = ADC()
# adc.configureClock(MS_s = origRateMHz)
# adc.configureTrigger(source='INT')

# for i in range(numberTraces):
#     now = time.perf_counter()
    
#     # acquire data
#     print('Starting acquisition {}'.format(i))
#     timestamp = time.strftime("%Y%m%d_%H%M%S")
#     savefile = path + 'NBR07_{}.bin'.format(timestamp)
#     # write metadata to corresponding .txt file
#     with open(savefile[0:-4] + ".txt",'w') as f:
#         from time import strftime
#         f.write(strftime("%c")+'\n')
#         f.write("Channels: " + 'AB' + '\n')
#         f.write("Acquisition duration: " + str(acquisitionLength_sec) + " seconds." + '\n')
#         f.write("Sample Rate MHz: " + str(actualSampleRateMHz) + '\n')


#     Creturn = subprocess.getoutput('"{}" {} {} "{}"'.format(pathToExe,int(acquisitionLength_sec),samplesPerPoint,savefile))
    
#     time.sleep(nMinutesDelay*60 - (time.perf_counter() - now))
    #sleep(60)