# -*- coding: utf-8 -*-
import os
import time
import Labber
import subprocess
import numpy as np
import fitTools.quasiparticleFunctions as qp
import matplotlib.pyplot as plt
import matplotlib.colors as mplc
from scipy.optimize import curve_fit, minimize
from fitTools.utilities import dBm2Watt, Watt2dBm
from time import perf_counter, sleep

pathToExe = r'C:/Users/LFL/lflPython/AlazarDrivers/CS_Average/x64/Release/ATS9371_CS_Average.exe'

client = Labber.connectToServer(timeout=None)
LO = client.connectToInstrument('Rohde&Schwarz RF Source',
                                dict(interface='TCPIP',address='192.168.1.128',startup='Get config'))
SMU = client.connectToInstrument('Keithley 2400 SourceMeter',dict(interface='GPIB',address='23',startup='Get config'))
SMUj = client.connectToInstrument('Keithley 2400 SourceMeter',dict(interface='GPIB',address='18',startup='Get config'))
VNA = client.connectToInstrument('Agilent Network Analyzer E5071B',dict(interface='GPIB',address='17',startup='Get config'))
SA = client.connectToInstrument('HP Spectrum Analyzer',dict(interface='GPIB',address='30',startup='Get config'))
PUMP = client.connectToInstrument('SignalCore SC5511A Signal Generator',dict(name='10002F25',startup='Get config'))
DA = client.connectToInstrument('Vaunix Lab Brick Digital Attenuator',dict(interface='USB',address='24679',startup='Get config'))

################
## THESE ARE ONLY VALID FOR THIS RUN!!! 6/14/22
###############
def curFunc(phi):
    return phi*13.1592 - 3.560075 # returns the current in mA for NBR07. ONLY VALID THIS RUN.
def freqFunc(fl):
    w0 = 4.3003788
    q0 = 0.0120375
    return w0*(1+q0*np.sin(np.pi*fl/2)*np.arctanh(np.sin(np.pi*fl/2))/(1-np.sin(np.pi*fl/2)*np.arctanh(np.sin(np.pi*fl/2))))**(-0.5)

###############
# fit multiple modes in VNA data
###############
def sumLor(f,A1,A2,A3,f1,shift,Gamma):
    return 1 - A1/(1+(2*(f-f1)/Gamma)**2) - A2/(1+(2*(f-(f1-shift))/Gamma)**2) - A3/(1+(2*(f-(f1-2*shift))/Gamma)**2)
def Lor(f,A1,f1,Gamma):
    return 1 - A1/(1+(2*(f-f1)/Gamma)**2)


##############
# JPA tuneup optimization function
############
def tuneup(x):
    # record 10 traces to average
    p = x[0]
    fl = x[1]
    SMUj.setValue('Source current',fl,rate=0.0005)
    PUMP.setValue('Power',p)
    SAsig = np.zeros(401)
    for _ in range(20):
        sleep(1.5)
        dSA = SA.getValue('Signal')
        SAsig += dBm2Watt(dSA['y'])
        
    xSA = np.arange(dSA['t0'],dSA['t0']+dSA['shape'][0]*dSA['dt'],dSA['dt'])
    SAsig /= 20
    max_ind=np.argmax(SAsig)
    max_val=np.max(SAsig)
    mask = np.logical_or(xSA < xSA[max_ind]-10e3, xSA > xSA[max_ind]+10e3)
    noise=SAsig[mask]
    avg_noise=np.mean(noise)
    snr = Watt2dBm(max_val)-Watt2dBm(avg_noise)
    print(f'P = {p:.2f} | F = {fl:.5f} | snr = {snr:.4f}')
    return -snr

#nHours = 12
#nMinutesDelay = 30
#numberTraces = nHours*60//nMinutesDelay
numberTraces = 1
acquisitionLength_sec = 5
origRateMHz = 500
# avgTime = 3e-6
sampleRateMHz = 1 # Note this should always be a integer factor of origRateMHz. Such as 15 x 20 = 300.
DAsetting = 20
T = 30

# LO.setValue('Frequency',LOfrequency*1e9)
PHIS = np.arange(0.47,0.4685,-0.001)
highI = curFunc(0.3) # mA
lowI = curFunc(0.4) # mA
lfVNA = Labber.createLogFile_ForData('test4_autoTuneNBR07',
                                     [{'name':'VNA - S21','complex':True,'vector':True,'x_name':'Frequency','x_unit':'Hz'}],
                                     step_channels=[{'name':'Phi','values':PHIS,'unit':'flux quanta'}])
tuneGuess = [-5,-26.95e-3]
for ph in PHIS:
    now = perf_counter()
    # get the current and freq mapping from flux fits
    estimated_freq = freqFunc(ph)*1e9
    I = curFunc(ph) # mA
    
    # do I tune the resonator high or low?
    if ph <= 0.35:
        SMU.setValue('Source current',lowI*1e-3,rate=0.0001)
    else:
        SMU.setValue('Source current',highI*1e-3,rate=0.0001)
    
    # with resonator tuned away, take VNA data for background
    VNA.setValue('Range type','Center - Span')
    VNA.setValue('Center frequency', estimated_freq-1e6)
    VNA.setValue('Span',5e6)
    VNA.setValue('Output enabled',True)
    VNA.setValue('Output power',-20)
    VNA.setValue('# of averages',500)
    VNA.setValue('Trigger',True)
    dBG = VNA.getValue('S21')
    xBG = np.arange(dBG['t0'],dBG['t0']+dBG['shape'][0]*dBG['dt'],dBG['dt'])
    zBG = dBG['y']
    
    # bring the resonator to the correct flux
    SMU.setValue('Source current',I*1e-3,rate=0.0001)
    
    # take VNA trace of resonator
    VNA.setValue('Trigger',True)
    dData = VNA.getValue('S21')
    zData = dData['y']/zBG
    
    lfVNA.addEntry({'x':xBG,'VNA - S21':zData})
    
    try:
        X = xBG*1e-9
        pars,cov = curve_fit(sumLor,X,zData.real,p0 = [0.8,0.5,0.1,estimated_freq*1e-9,3e-4,0.00025],bounds=(0,np.infty))
        plt.plot(X,zData.real,label='0')
        plt.plot(X,sumLor(X,*pars),label='fit')
        plt.axvline(pars[3])
        plt.axvline(pars[3]-pars[4])
        plt.axvline(pars[3]-2*pars[4])
        plt.legend()
        plt.show()
        plt.close()
        f0 = pars[3]
        fd = pars[3]-pars[4]
    except:
        X = xBG*1e-9
        pars,cov = curve_fit(Lor,X,zData.real,p0 = [0.8,estimated_freq*1e-9,0.00025],bounds=(0,np.infty))
        plt.plot(X,zData.real,label='0')
        plt.plot(X,sumLor(X,*pars),label='fit')
        plt.axvline(pars[1])
        plt.legend()
        plt.show()
        plt.close()
        f0 = pars[1]
        fd = pars[1] - 1.5e-9*(qp.f_n_phi(ph,0)-qp.f_n_phi(ph,1))
    
    # turn off VNA, turn on sig gen at fd, turn on pump at 2(fd+3MHz)
    VNA.setValue('Output enabled',False)
    LO.setValue('Frequency',fd*1e9)
    LO.setValue('Output',True)
    PUMP.setValue('Frequency',2*(fd*1e9 + 3e6))
    PUMP.setValue('Output status',True)
    
    # configure SA
    SA.setValue('Center frequency',fd*1e9)
    SA.setValue('Span',1e6)
    SA.setValue('IF bandwidth',3e3)
    
    # optimize JPA using minimize func
    optRes = minimize(tuneup,tuneGuess,method='L-BFGS-B',bounds=[(-5,7),(-27.3e-3,-26.6e-3)],tol=0.05,options={'eps':np.array([0.5,0.1e-3])})
    print(f'Successful optimization = {optRes["success"]}\n')
    tuneGuess = optRes['x']
    SMUj.setValue('Source current',tuneGuess[1],rate=0.0005)
    PUMP.setValue('Power',tuneGuess[0])
    
    # Take Alazar data
    StringForFlux = r'{}GHz_DA{}_SR{}MHz'.format(fd,DAsetting,sampleRateMHz)
    path = r"G:\Shared drives\LFL\Projects\Quasiparticles\NBR19_Jun14_2022\testAutoTune\{}\\".format(StringForFlux)
    figpath = r"G:\Shared drives\LFL\Projects\Quasiparticles\NBR19_Jun14_2022\testAutoTune\Figures\\"
    
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
        f.write("LO frequency: "+str(fd) + " GHz")
        f.write("flux bias: "+str(I) + " mA")
        f.write("DA setting: "+str(DAsetting) + " dB\n")
        f.write("Temperature: "+str(T)+' mK\n')
        f.write("PHI: "+str(ph))
    
    
    Creturn = subprocess.getoutput('"{}" {} {} "{}"'.format(pathToExe,int(acquisitionLength_sec),samplesPerPoint,savefile))
    
    print(Creturn)
    
    data = qp.loadAlazarData(savefile)
    data = qp.uint16_to_mV(data)
    ax = qp.plotComplexHist(data[0],data[1])
    ax.set_title(f'PHI = {ph:.4f}')
    plt.savefig(figpath+f'\\{ph*1000}.png')
    plt.show()
    plt.close()
    
    # Turrn off JPA pump and LO
    LO.setValue('Output',False)
    PUMP.setValue('Output status',False)
    print(f'This step took {perf_counter()-now:.2} seconds')

    


#     StringForFlux = r'{}GHz_DA{}_SR{}MHz'.format(LOfrequency,DAsetting,sampleRateMHz)
#     path = r"G:\Shared drives\LFL\Projects\Quasiparticles\NBR19_Jun13_2022\fluxSweep\{}\\".format(StringForFlux)
#     figpath = r"G:\Shared drives\LFL\Projects\Quasiparticles\NBR19_Jun13_2022\fluxSweep\Figures\\"

#     if not os.path.exists(path):
#         os.makedirs(path)
#     if not os.path.exists(figpath):
#         os.makedirs(figpath)

#     timestamp = time.strftime("%Y%m%d_%H%M%S")
#     savefile = path + 'NBR19_{}.bin'.format(timestamp)

#     samplesPerPoint = int(max(origRateMHz/sampleRateMHz,1))
#     actualSampleRateMHz = origRateMHz/samplesPerPoint

#     # write metadata to corresponding .txt file
#     with open(savefile[0:-4] + ".txt",'w') as f:
#         from time import strftime
#         f.write(strftime("%c")+'\n')
#         f.write("Channels: " + 'AB' + '\n')
#         f.write("Acquisition duration: " + str(acquisitionLength_sec) + " seconds." + '\n')
#         f.write("Sample Rate MHz: " + str(actualSampleRateMHz) + '\n')
#         f.write("LO frequency: "+str(LOfrequency) + " GHz")
#         f.write("flux bias: "+str(I) + " A")
#         f.write("DA setting: "+str(DAsetting) + " dB\n")
#         f.write("Temperature: "+str(T)+' mK\n')
#         f.write("Victor current: "+str(I*1000)+' mA\n')


#     Creturn = subprocess.getoutput('"{}" {} {} "{}"'.format(pathToExe,int(acquisitionLength_sec),samplesPerPoint,savefile))

#     print(Creturn)

#     data = qp.loadAlazarData(savefile)
#     data = qp.BoxcarDownsample(data,2e-6,10e6)
#     data = qp.uint16_to_mV(data)
#     # ax = qp.plotComplexHist(data[0],data[1])
#     # ax.set_title(f'{I*1e3:.1f} mA')
#     # plt.savefig(figpath+f'\\{I*1e6}uA.png')
#     # plt.show();
#     # plt.close();
#     x.append(np.mean(data[0]))
#     y.append(np.mean(data[1]))

#     fig,ax = plt.subplots()
#     # hi = plt.hist2d(data[0],data[1],bins=(80,80),cmap=plt.get_cmap('Greys'))
#     ax,hi = qp.plotComplexHist(data[0],data[1],returnHistData=True)
#     # hi = np.histogram2d(data[0],data[1],bins=(200,200))
#     xc = (hi[1][:-1]+hi[1][1:])/2
#     yc = (hi[2][:-1]+hi[2][1:])/2
#     # guess = [60000,np.mean(data[0]),np.mean(data[1]),1,1,0]
#     # xx,yy,amps,means,varis = qp.fitGaussian(hi,guess)
#     # # f = gaussianMix(heights,widths,means)
#     # qp.make_ellipses2(means,varis,ax,['red'])
#     ax.set_title(f'{I*1e3:.1f} mA')
#     plt.savefig(figpath+f'\\{I*1e6}uA.png')
#     plt.show()
#     plt.close()
#     # print(varis)

# fig,ax = plt.subplots(1,1,'none',figsize=[4,3],constrained_layout=True)
# colors = plt.get_cmap('gist_rainbow', len(x))
# norm = mplc.Normalize(vmin=0, vmax=len(x))
# sm = plt.cm.ScalarMappable(cmap=colors, norm=norm)
# sm.set_array([])
# fig.colorbar(sm, aspect=60)
# plt.plot(x,y)
# for i,(xx,yy) in enumerate(zip(x,y)):
#     plt.scatter(xx,yy,c=colors(i))
# plt.savefig(figpath+r'summary.png')
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
