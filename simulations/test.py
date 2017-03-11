#!/usr/bin/env python

from __future__ import division
import subprocess, imp, os, csv, time
start_time = time.time()
#this file runs every case in a defined basic scenario (reference case).
#This reference case considers actuated traffic lights with a phase duration of
#40 second, a minDur of 5 seconds and a maxDur of 60 seconds.

path = os.getcwd() #ends without /
is 
#the network is not required to be defined in this file because it was already generated in the train.py file, 
#which is supposed to be executed before this file, but if this file wants to be executed by itself, this option 
#should be set to true

network = False

#simulation global parameters
n = 5
l = 150
nlanes = 3
frequency = 60

#auxiliary function
def checkDirectory(path):
	directory = os.path.dirname(path)
	if not os.path.exists(directory):
		os.mkdir(directory)
	
######################
#GENERATES THE NETWORK
######################
modl = imp.load_source('networkgenerator', path + '/simGen/networkgenerator.py')
import networkgenerator
modl = imp.load_source('files', path + '/pythons/files.py')
import files
modl = imp.load_source('tripsGenerator', path + '/simGen/tripsGenerator.py')
import tripsGenerator

checkDirectory('netDef/')
checkDirectory('netDef/csv/')
checkDirectory('netDef/xml/')
checkDirectory('input/')

#generates the network
networkgenerator.networkgenerator(l,n, nlanes)

#generates the necessary files (C.dat, J.dat, E.dat ...)
checkDirectory('postprocess/data/')
files.dat()

####################
#AUXILIARY FUNCTIONS
####################
#these functions are used to elaborate the summary tables containing the travel times
def getTimes(case, maxDur):
    totalTime = 0;
    totalLoss = 0;
    n = 0
    number = {}
    cumTime = {}
    cumLoss = {}
    tripinfo = open ("output/train/csv/tripinfo/tripinfo{case}_{maxDur}.csv".format(case = case, maxDur = maxDur), 'r')
    reader = csv.reader(tripinfo, delimiter = ';')
    row = next(reader)
    posTime = row.index('tripinfo_duration')
    posOrig = row.index('tripinfo_departLane')
    posDest = row.index('tripinfo_arrivalLane')
    posLoss = row.index('tripinfo_timeLoss')    
    for row in reader:
        totalTime += float(row[posTime])
        totalLoss += float(row[posLoss])
        n += 1
        trip = getTrip(row[posOrig], row[posDest])
        if trip in number.keys():
            number[trip] += 1
            cumTime[trip] += float(row[posTime])
            cumLoss[trip] += float(row[posLoss])
        else:
            number[trip] = 1
            cumTime[trip] = float(row[posTime])
            cumLoss[trip] = float(row[posLoss])
    meanTime = totalTime/n
    meanLoss = totalLoss/n
    means = []
    meansLoss = []
    for k in number.keys():
        means.append(cumTime[k]/number[k])
        meansLoss.append(cumLoss[k]/number[k])
    maxTime = max(means)
    maxLoss = max(meansLoss)
    return meanTime, maxTime, meanLoss, maxLoss
            

def getTrip(departLane, arrivalLane):
    departEdge = departLane[0:(departLane.index('_')-1)]
    arrivalEdge = arrivalLane[0:(arrivalLane.index('_')-1)]
    return departEdge + '->' + arrivalEdge

##################
#RUNNING THE CASES
##################
cases = ['case0', 'case1', 'case2', 'case3', 'case4', 'case5', 'case6', 'case7']
values = range(10,61,5)

header =  [False]*len(values)

checkDirectory('output/')

checkDirectory('output/test/')
checkDirectory('output/test/detectors/')
checkDirectory('output/test/tripinfo/')

checkDirectory('output/train/')
checkDirectory('output/train/files/')
checkDirectory('output/train/files/nVeh/')
checkDirectory('output/train/files/occupancy/')
checkDirectory('output/train/files/speed/')
checkDirectory('output/train/files/times/')
checkDirectory('output/train/files/times/travelTime/')
checkDirectory('output/train/files/times/timeLoss/')
checkDirectory('output/train/csv/')
checkDirectory('output/train/csv/detectors/')
checkDirectory('output/train/csv/tripinfo/')

checkDirectory('output/xml/')

#run train data
start_train = time.time()
tsim =10*3600
seed = 10
#generates de configuration file
files.configuration(tsim)
for case in cases:
    start_traffic = time.time()
    print '-------- Generating traffic files --------'
    timesDoc = open("output/train/files/times/travelTime/" + case + ".csv", 'w')
    timesDoc.write('maxDur;meanTime;maxTime\n')
    timesLoss = open("output/train/files/times/timeLoss/" + case + "Loss.csv", 'w')
    timesLoss.write('maxDur;meanLoss;maxLoss\n')
    
    #generates the traffic for the simulation
    tripsGenerator.writeTrips(0, tsim, case, seed)	
    subprocess.call(["duarouter", "-n", "input/mapa.net.xml", "-t", "input/trips.trips.xml", "-o", "input/rutes.rou.xml", "--unsorted-input", "true", "--ignore-errors", "true", "--departspeed", "10", "--departlane", "free"])    
    
    print 'Traffic generation time: {} seconds'.format(str(time.time() - start_traffic))
    print ''

    for i in range(len(values)):
        maxDur = values[i]
        print '-------- Simulating {case} with  maxDur {maxDur} seconds --------'.format(case = case, maxDur = maxDur)
		#generate additional file for the simulation
        files.additional(maxDur, frequency)
     
        #runs the simulation
        start_simulation = time.time()
        subprocess.call(["sumo", "-c", "configuration.sumocfg", "--xml-validation", "never", "--time-to-teleport", "-1"])
        print ''
        os.system("$SUMO_HOME/tools/xml/xml2csv.py output/xml/tripinfo.xml -o output/train/csv/tripinfo/tripinfo{case}_{maxDur}.csv".format(case = case, maxDur = maxDur))
        os.system("$SUMO_HOME/tools/xml/xml2csv.py output/xml/detectors.xml -o output/train/csv/detectors/detectors{case}_{maxDur}.csv".format(case = case, maxDur = maxDur))
        print 'Simulation and conversion time {} seconds'.format(str(time.time() - start_simulation))
		
        #write the detectors measures in the csv
        subprocess.call(["Rscript", "postprocess/codes/writeDetectorsCsv.R", str(maxDur), case, str(header[i])])
        header[i] = True    #once we have written the header it must be true, to avoid writing it again
        start_writecsv = time.time()        
        #travel times depending on tls configuration
        meanTime, maxTime, meanLoss, maxLoss = getTimes(case, maxDur);
        timesDoc.write(str(maxDur) + ';' + str(meanTime) + ';' + str(maxTime) + '\n')
        timesLoss.write(str(maxDur) + ';' + str(meanLoss) + ';' + str(maxLoss) + '\n')
        print 'Writing travel times: {} seconds'.format(str(time.time() - start_writecsv))         
        print ''
    timesDoc.close()
    timesLoss.close()

print 'Total time of running train simulations: {} seconds'.format(str(time.time() - start_train))

#cost function

maxDurRef
#running the test data
start_test = time.time()
tsim =5*3600
seed = 20
#generates de configuration file
files.configuration(tsim)
for case in cases:
    start_traffic = time.time()
    print '-------- Generating traffic files --------'
    #generates the traffic for the simulation
    tripsGenerator.writeTrips(0, tsim, case, seed)	
    subprocess.call(["duarouter", "-n", "input/mapa.net.xml", "-t", "input/trips.trips.xml", "-o", "input/rutes.rou.xml", "--unsorted-input", "true", "--ignore-errors", "true", "--departspeed", "10", "--departlane", "free"])    
    print 'Traffic generation time: {} seconds'.format(str(time.time() - start_traffic))
    print ''

    print '-------- Simulating {case} with  maxDur {maxDur} (reference value) seconds --------'.format(case = case, maxDur = maxDurRef)
    #generate additional file for the simulation
    files.additional(maxDurRef, frequency)
    #runs the simulation
    start_simulation = time.time()
    subprocess.call(["sumo", "-c", "configuration.sumocfg", "--xml-validation", "never", "--time-to-teleport", "-1"])
    print ''
    os.system("$SUMO_HOME/tools/xml/xml2csv.py output/xml/tripinfo.xml -o output/test/tripinfo/tripinfo{case}_{maxDur}.csv".format(case = case, maxDur = maxDurRef))
    os.system("$SUMO_HOME/tools/xml/xml2csv.py output/xml/detectors.xml -o output/test/detectors/detectors{case}_{maxDur}.csv".format(case = case, maxDur = maxDurRef))
    print 'Simulation and conversion time {} seconds'.format(str(time.time() - start_simulation))	
        
    #write the detectors measures in the csv
    #subprocess.call(["Rscript", "postprocess/codes/writeDetectorsCsv.R", str(maxDurRef), case, str(header[i])])
    #header[i] = True    #once we have written the header it must be true, to avoid writing it again
    #start_writecsv = time.time()        
    
    #print 'Writing travel times: {} seconds'.format(str(time.time() - start_writecsv))         
    #print ''

print 'Total time of running test simulations: {} seconds'.format(str(time.time() - start_test))
print ''
print 'Total time of execution: {} seconds'.format(str(time.time() - start_time))

os.system('rm -r output/xml/')

    Contact GitHub API Training Shop Blog About 

