import os
import datetime
import glob
import string
import shapelib
import dbflib
import time
import sys
import csv
import shapefile
import geopandas as gpd
import gurobipy as gb
import numpy as np
from dbfpy import dbf
from dateparser import parse
from shapely.geometry import Point, Polygon, LineString

def ensure_dir(directory):
    # directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)

def formatizeTempDate(tempDate):
    tempDate = string.replace(tempDate, "-", "")
    tempDate = string.replace(tempDate, " ", "T")
    tempDate = string.replace(tempDate, ":", "")
    return tempDate

def addingCleanedFieldForIntervalShapeFiles(tempDate,cleanTargetStep):
    fileNamePattern = 'Transport1-'
    overAllfileName = './ShapeData/' + fileNamePattern + tempDate + '.dbf'
    print 'cleaning the file %s' % (overAllfileName)
    r = shapefile.Reader(overAllfileName)
    w = shapefile.Writer(r.shapeType)
    w.fields = list(r.fields)
    w.field("CLEANED", "C", "20")
    for rec in r.records():
        rec.append(0)
        w.records.append(rec)
    w._shapes.extend(r.shapes())
    w.save(r'data/CUT' + str(cleanTargetStep*100) +'/'+ fileNamePattern + tempDate + '_cleaned.dbf')

def updatingNextDayShapeFile(currentDate,iValue,parsedDate2,modelRuntime2,cleanTargetStep):
    print 'Removing cleaned rows from the following day of Transport1-%s.shp' % requiredDate
    startTime = time.time()
    # print 'time now: %f' % float(startTime)
    rowsToBeRemoved = []
    parcelNumberFieldNumber = 0
    r2 = shapefile.Reader("data/CUT"+ str(cleanTargetStep*100) +"/Transport1-%s_cleaned" % currentDate)
    allFields = r2.fields

    j = 0
    for eachField in allFields:
        if eachField[0] == 'PARCEL_NUM':
            parcelNumberFieldNumber = j
        else:
            j += 1

    # print parcelNumberFieldNumber

    i = 0
    cleanedFieldNumber = 0
    for eachField in allFields:
        if eachField[0] == 'CLEANED':
            cleanedFieldNumber = i
        else:
            i += 1

    # print cleanedFieldNumber

    for rec in r2.records():
        if rec[cleanedFieldNumber - 1] == '1':
            rowsToBeRemoved.append(rec[parcelNumberFieldNumber - 1])

    rowsToBeRemoved.append(None)

    # if iValue != modelRuntime2:
    requiredDate2 = str(datetime.datetime.strptime(parsedDate2, '%Y-%m-%d %H:%M:%S') + datetime.timedelta(days=iValue))
    requiredDate2 = string.replace(requiredDate2, "-", "")
    requiredDate2 = string.replace(requiredDate2, " ", "T")
    requiredDate2 = string.replace(requiredDate2, ":", "")

    # print currentDate
    # print requiredDate2

    rf = shapefile.Reader("./ShapeData/Transport1-%s" % requiredDate2)

    wf = shapefile.Writer(rf.shapeType)

    wf.fields = list(rf.fields)

    i = 0
    for rec in rf.records():
        if rec[parcelNumberFieldNumber - 1] != rowsToBeRemoved[i]:
            wf.records.append(rec)
        else:
            i += 1
    wf._shapes.extend(rf.shapes())
    wf.save("./ShapeData/Transport1-%s_updated" % requiredDate2)
    endTime = time.time()
    # print 'time now: %f' % float(endTime)
    print 'time elapsed: %f seconds' % float(endTime - startTime)

def addingCleanedAttribute(currentDate,cleanTargetStep):
    print 'Adding \'Cleaned\' field for Transport1-%s.shp' % requiredDate
    startTime = time.time()
    # print 'time now: %f' % float(startTime)
    solutionFile = open('data/CUT'+ str(cleanTargetStep*100) +'/OSCOM_%s_sol.txt' % currentDate)
    cleanedLines = []
    for line in solutionFile.readlines():
        if line.__contains__('u'):
            numberObtained = int(line[11:-1])
            cleanedLines.append(numberObtained)
    cleanedLines.append(None)

    r = shapefile.Reader("./ShapeData/Transport1-%s" % currentDate)

    w = shapefile.Writer(r.shapeType)

    w.fields = list(r.fields)

    w.field("CLEANED", "C", "20")

    i = 1
    j = 0

    for rec in r.records():
        if i == cleanedLines[j]:
            rec.append(1)
            i += 1
            j += 1
        else:
            rec.append(0)
            i += 1

        w.records.append(rec)

    w._shapes.extend(r.shapes())

    w.save("data/CUT"+ str(cleanTargetStep*100) +"/Transport1-%s_cleaned" % currentDate)
    endTime = time.time()
    # print 'time now: %f' % float(endTime)
    print 'time elapsed: %f seconds' % float(endTime - startTime)

def gbSolveOSCOM(modelFile, logFil, resultFil):
    print 'solving model file OSCOM_%s.lp using Gurobi' % requiredDate
    startTime = time.time()
    # print 'time now: %f' % float(startTime)
    mod = gb.read(modelFile)
    mod.reset()
    mod.setParam('LogFile', logFil)
    mod.setParam('MIPGap', 0.0)
    mod.setParam('TimeLimit', 40000000)
    # mod.setParam('MIPFocus', 2.0)
    mod.optimize()
    rf = open(resultFil, 'w')
    xSol = []
    for deVar in mod.getVars():
        if deVar.VarName.startswith('u'):
            if deVar.X > 0.99:
                rf.write("%f, %s" % (deVar.X, deVar.VarName))
                rf.write("\n")
                xSol.append(int(deVar.VarName.split('u')[1]))
        else:
            if deVar.X > 0.00:
                rf.write("%f, %s" % (deVar.X, deVar.VarName))
                rf.write("\n")
            if deVar.VarName.startswith('z1'):
                z1 = deVar.X

    endTime = time.time()
    # print 'time now: %f' % float(endTime)
    print 'time elapsed: %f seconds' % float(endTime - startTime)
    return [z1, mod.NumConstrs, mod.NumVars, mod.Runtime, mod.ObjVal, xSol]



def generateOSCOMInputs(rampFilePath, spillFilePath, containRadius, distThreshold):
    rampShp = shapelib.ShapeFile(rampFilePath)
    rampDbf = dbflib.DBFFile(rampFilePath[:-4] + '.dbf') # rampFilePath.split('.')[0]
    spillShp = shapelib.ShapeFile(spillFilePath)
    spillDbf = dbflib.DBFFile(spillFilePath[:-4] + '.dbf') # spillFilePath.split('.')[0]

    vesCapList = []
    rampGeoList = []
    tn = rampDbf.record_count()
    for j in range(tn):
        rampObj = rampShp.read_object(j)
        rampGeo = Point(tuple(rampObj.vertices()[0]))
        rampGeoList.append(rampGeo)

        recordDict = rampDbf.read_record(j)
        vesCapList.append(recordDict['VesCap'])

    distDict = {}
    serveDict = {}
    coverDict = {}
    volumeList = []
    spillGeoList = []
    sn = spillDbf.record_count()

    for j in range(sn):
        serveDict[j] = []
        spillObj = spillShp.read_object(j)
        spillGeo = Point(tuple(spillObj.vertices()[0]))
        spillGeoList.append(spillGeo)

        recordDict = spillDbf.read_record(j)
        volumeList.append(recordDict['VOLUME_BBL']*42)

        for i in range(tn):
            dist = rampGeoList[i].distance(spillGeo)
            if dist <= distThreshold:
                distDict[(i, j)] = dist
                serveDict[j].append(i)

    servedDict = {}
    for i in range(tn):
        servedDict[i] = []
        for k, v in serveDict.items():
            if i in v:
                servedDict[i].append(k)

    for j in range(sn):
        coverDict[j] = []
        for l in range(sn):
            sdist = spillGeoList[j].distance(spillGeoList[l])
            if sdist <= containRadius:
                coverDict[j].append(l)

    print 'done'

    return [vesCapList, volumeList, distDict, serveDict, servedDict, coverDict]


def generateOSCOM(rampFilePath, spillFilePath, containRadius, operCap, cleanTarget, distThreshold, outFilePath):
    """
    Input:
    "rampFilePath": The response equipment storage location shapefile: path to the shapefile (string type)
    "spillFilePath": The oil spill point shapefile: path to the shapefile (string type)
    "containRadius": The coverage radius of the containment booms (double type)
    "operCap": The storage capacity of the vessel (double type)
    "cleanTarget": The speed of the vessel (double type)
    "distThreshold": The distance threshold to allow a vessel dispatch (double type)
    "outFilePath": The clean up target goal for oil spill (double type)

    Output:
    "outFilePath": The optimization model file (.lp)

    """
    vesCapList, volumeList, distDict, serveDict, servedDict, coverDict = generateOSCOMInputs(rampFilePath, spillFilePath, containRadius, distThreshold)

    outputFile = open(outFilePath, 'w')

    outputFile.write('Minimize z1')
    outputFile.write('\n')
    outputFile.write('Subject To')
    outputFile.write('\n')

    xVarList = []

    outputFile.write('obj: z1')
    for k, v in distDict.items():
        outputFile.write(' - %f x%dj%d' % (v, k[0], k[1]))
        xVarList.append('x%dj%d' % (k[0], k[1]))
    outputFile.write(' = 0\n')

    vn = len(volumeList)
    cn = len(vesCapList)

    for i, vesCap in enumerate(vesCapList):
        if servedDict[i]:
            outputFile.write('cap%d: ' % (i,))
            for jj, j in enumerate(servedDict[i]):
                if jj != (len(servedDict[i]) - 1):
                    outputFile.write('x%dj%d + ' % (i, j))
                else:
                    outputFile.write('x%dj%d <= %d\n' % (i, j, vesCap))

    for k, v in coverDict.items():
        if len(v) == 0:
            continue
        outputFile.write('link%d: ' % (k,))
        for ivv, vv in enumerate(v):
            for ii, i in enumerate(serveDict[vv]):
                if ii == (len(serveDict[vv]) - 1) and ivv == (len(v) - 1):
                    outputFile.write('x%dj%d - u%d >= 0\n' % (i, vv, k))
                else:
                    outputFile.write('x%dj%d + ' % (i, vv))

    uVarList = []
    totalSpill = sum(volumeList)
    outputFile.write('target: ')
    for j, volume in enumerate(volumeList):
        uVarList.append('u%d' % (j,))
        if j != (vn - 1):
            outputFile.write('%f u%d + ' % (volume, j))
        else:
            outputFile.write('%f u%d >= %f\n' % (volume, j, cleanTarget * totalSpill))

    outputFile.write('Binary')
    outputFile.write('\n')

    for i, vv in enumerate(uVarList):
        outputFile.write(' %s' % (vv,))

        if i % 11 == 0:
            outputFile.write('\n')
            outputFile.write(' ')

    outputFile.write('\n')
    outputFile.write('General')
    outputFile.write('\n')

    for i, vv in enumerate(xVarList):
        outputFile.write(' %s' % (vv,))

        if i % 11 == 0:
            outputFile.write('\n')
            outputFile.write(' ')

    outputFile.write('\n')
    outputFile.write('End')

####The actual program starts at this point ####
if __name__ == '__main__':
#Checking if the required directories are present or not. If not, creating them
    realpath = os.path.abspath("./data/")
    realpath2 = os.path.abspath("./data/CUT75.0/")
    realpath3 = os.path.abspath("./data/CUT80.0/")
    realpath4 = os.path.abspath("./data/CUT85.0/")
    realpath5 = os.path.abspath("./data/CUT90.0/")
    realpath6 = os.path.abspath("./data/CUT95.0/")
    realpath7 = os.path.abspath("./data/CUT0.0/")
    realpath8 = os.path.abspath("./data/SpatialJoinFiles/")
    realpath9 = os.path.abspath("./data/SDSSFiles/")

    path_exists = os.path.exists(realpath)
    path_exists2 = os.path.exists(realpath2)
    path_exists3 = os.path.exists(realpath3)
    path_exists4 = os.path.exists(realpath4)
    path_exists5 = os.path.exists(realpath5)
    path_exists6 = os.path.exists(realpath6)
    path_exists7 = os.path.exists(realpath7)
    path_exists8 = os.path.exists(realpath8)
    path_exists9 = os.path.exists(realpath9)

    if not (path_exists and path_exists2 and path_exists3 and path_exists3 and path_exists4 and path_exists4 and path_exists5 and path_exists6 and path_exists7 and path_exists8 and path_exists9):
        print "One or more of the required directories not present! Creating them now..."
        ensure_dir(realpath)
        ensure_dir(realpath2)
        ensure_dir(realpath3)
        ensure_dir(realpath4)
        ensure_dir(realpath5)
        ensure_dir(realpath6)
        ensure_dir(realpath7)
        ensure_dir(realpath8)
        ensure_dir(realpath9)

    #Few basic parameters are set
    containRadius = 1769
    operCap = 62400
    speed = 22224
    hours = 16
    distThreshold = speed * hours
    cleanTarget = 0.95

    #The inputs of the simulation are taken from this file.
    simulationInputsFile = open('./ShapeData/inputs.txt')

    #The inputs files which has been read into 'simulationInputsFile' variable are now parsed below
    for line in simulationInputsFile.readlines():
        if line.__contains__('Start date:'):
            #the start date of the simulation is obatained
            startDate = line[12:-1]
            print 'the start date of the simulation is %s \n' %startDate

        if line.__contains__('Runtime:') and not line.__contains__('Blowout Runtime:'):
            #the overall model run time of the simulation is obtained here (11 days or 12 days, etc.)
            modelRuntimeOriginal = line[9:-1]
            print 'the overall runtime  of the simulation is %s \n' % modelRuntimeOriginal

        if line.__contains__('Blowout Runtime:'):
            #the duration for which the blowout lasts is obtained here
            blowoutRuntime = line[17:-1]
            print 'the duaration of the blowout alone is %s \n' % blowoutRuntime

        if line.__contains__('Interval:') and not (line.__contains__('hour interval:') or line.__contains__('Output Interval ')):
            #the interval at which the simulation is recorded is obtained here
            recordingInterval = int(line[14:-3])
            print 'the interval at whcih the simulation is recorded is %s \n' % recordingInterval

    #the start date obtained above is parsed as a string
    parsedDate = str(parse(startDate))
    parsedDate = parsedDate[0:-6]

    # similarly, the model runtime obtained above is parsed as an integer
    modelRuntime = int(modelRuntimeOriginal[0:2])

    # similarly, the blowout duration obtained above is parsed as an integer
    blowoutRuntimeTruncated = int(blowoutRuntime[0:2])

    # PART 1
    # Important Dates .csv generator  starts
    # this part generates a csv file with the start date, model runtime, blowout duration, and
    # the enddate  as the header and their values as the first row

    for i in range(0, modelRuntime + 1):
        impDateVar = str(datetime.datetime.strptime(parsedDate, '%Y-%m-%d %H:%M:%S') + datetime.timedelta(days=i))
        impDateVar = str(parse(impDateVar))

    with open("data/ImportantDates.csv", 'wb') as importantDatesCsv:
        writer = csv.writer(importantDatesCsv)
        writer.writerow(['StartDate', 'ModelRuntime', 'BlowoutDuration', 'EndDate'])
        writer.writerow([parsedDate, modelRuntime, blowoutRuntimeTruncated, impDateVar])
    importantDatesCsv.close()

    # Important Dates .csv generator  ends

    # PART 2
    # Actual Automation Starts Here:
    # Here, the entire process of optimization and required shape file generation happens for five times where
    # the cleanup target is changed for each iteration ////
    # The process first starts with 95% cleanup and proceeds till 75%

    for cleanTargetStepInterval in range(95,65,-5): #Goes till 75 only and then becomes 0
        if cleanTargetStepInterval == 70:
            cleanTargetStepInterval = cleanTargetStepInterval - 70
        # 95% can be represented as 0.95 but that leads to discrepancies in the loop variable for every iteration.
        # Hence, we go from 95 through 75 but divide it by 100 in the first step as shown below
        cleanTargetStep = (cleanTargetStepInterval/100.0) #here, cleanTargetStep contains 0.95 for first iteration, and so on tll 0.75

        #Value of parsedDate might have been changed in PART 1. Hence, we take the value again
        parsedDate = str(parse(startDate))
        parsedDate = parsedDate[0:-6]

        #Similarly for the modelRuntime as well
        modelRuntime = int(modelRuntimeOriginal[0:2])

        # Here, we first check if the recording interval is 24 hrs or not.
        # The least interval possible by BLOSOM is 3 hours which gives 8 sets of shapefiles for each day (3x8 =24).
        # If the interval is 6 hours, 4 sets of shapefiles are obtained for each day and so on (6x4 = 24)

        # Here, if the recording interval is less than 24 hours, we add a 'Cleaned' field and set its value to 0 because
        # these shapefiles are later merged with the cleaned shapefiles


        #Less than 24 hours recording interval case handling starts
        if recordingInterval < 24:
            for x in range(0, modelRuntime): #runs for the entire duration of the model runtime
                requiredDate = str(datetime.datetime.strptime(parsedDate, '%Y-%m-%d %H:%M:%S') + datetime.timedelta(days=x))
                stepValueHours = recordingInterval
                for y in range(0, 24, stepValueHours): #for every set of shapefiles of that day
                    if x != 0: #if not the first day shapefiles as they have either no values in the very first file or they are not cleaned on day 1
                        if y != 0: #from second day, we don't want to disturb the first set of shapefiles which start with 00:00 hh:mm because they are the ones that contain the cleaned parcels
                            tempDate = str(datetime.datetime.strptime(requiredDate, '%Y-%m-%d %H:%M:%S') + datetime.timedelta(hours=y))
                            tempDate = formatizeTempDate(tempDate)
                            addingCleanedFieldForIntervalShapeFiles(tempDate,cleanTargetStep)
                    else: #if it is the first day's shapefile, then we add 'Cleaned' attribute to all the shapefiles of that day as they are not cleaned until the following day
                        tempDate = str(datetime.datetime.strptime(requiredDate, '%Y-%m-%d %H:%M:%S') + datetime.timedelta(hours=y))
                        tempDate = formatizeTempDate(tempDate)
                        addingCleanedFieldForIntervalShapeFiles(tempDate,cleanTargetStep)
        # Less than 24 hours recording interval case handling ends
        #Basically all the intermediate files have been added with the attribute 'Cleaned' and assigned a value of 0 as they are not considered cleaned until the next day's 00:00 hh:mm shapefiles

        # Assuming that the interval is 24 hours here
        for i in range(0, modelRuntime+1): #runs for the entire duration of the model runtime
            requiredDate = str(datetime.datetime.strptime(parsedDate, '%Y-%m-%d %H:%M:%S') + datetime.timedelta(days=i))
            requiredDate = formatizeTempDate(requiredDate)

            if i == 1: #Day 1 set of shapefiles don't have any data for 24 hour recording interval, so we start from day 2 which is denoted by i=1
                print 'generating model file for Transport1-%s.shp' % requiredDate
                # OSCOM model file is generated
                if cleanTargetStep != 0.0:
                    generateOSCOM('./BoatRamps/BoatRamps_GOM_1.shp', './ShapeData/Transport1-%s.shp' % requiredDate, containRadius, operCap, cleanTargetStep, distThreshold, 'data/CUT'+ str(cleanTargetStep*100) +'/OSCOM_%s.lp' % requiredDate)
                # generated OSCOM model file is given as input to GUROBI for optimization or solving the model file
                if cleanTargetStep != 0.0:
                    gbSolveOSCOM('data/CUT'+ str(cleanTargetStep*100) +'/OSCOM_%s.lp' % requiredDate, 'data/CUT'+ str(cleanTargetStep*100) +'/OSCOM_%s_log.txt' % requiredDate, 'data/CUT'+ str(cleanTargetStep*100) +'/OSCOM_%s_sol.txt' % requiredDate)
                # Gurboi generates solution file and log file

                # We take the solution file and find out the list of the cleaned parcels and add a 'CLeaned' field with value 1 if its in the cleaned list or 0 otherwise
                addingCleanedAttribute(requiredDate,cleanTargetStep)
                # We take the solution file and find out the list of the cleaned parcels and remove them from the following day's shapefile
                if cleanTargetStep != 0.0:
                    updatingNextDayShapeFile(requiredDate,i+1,parsedDate,modelRuntime,cleanTargetStep)

            elif i > 1 and i < modelRuntime: #for all the days starting from day 3 and the one before the last day
                print 'generating model file for Transport1-%s_updated.shp' % requiredDate
                if cleanTargetStep != 0.0:
                    generateOSCOM('./BoatRamps/BoatRamps_GOM_1.shp', './ShapeData/Transport1-%s_updated.shp' % requiredDate, containRadius, operCap, cleanTargetStep, distThreshold, 'data/CUT' + str(cleanTargetStep * 100) + '/OSCOM_%s.lp' % requiredDate)
                if cleanTargetStep != 0.0:
                    gbSolveOSCOM('data/CUT' + str(cleanTargetStep * 100) + '/OSCOM_%s.lp' % requiredDate, 'data/CUT' + str(cleanTargetStep * 100) + '/OSCOM_%s_log.txt' % requiredDate, 'data/CUT' + str(cleanTargetStep * 100) + '/OSCOM_%s_sol.txt' % requiredDate)
                addingCleanedAttribute(requiredDate,cleanTargetStep)
                if cleanTargetStep != 0.0:
                    updatingNextDayShapeFile(requiredDate, i+1,parsedDate,modelRuntime,cleanTargetStep)

            elif i==modelRuntime: # for the last day file, there is no following day shapefile from where the cleaned parcels can be removed so
                # we stop with adding the 'Cleaned' field parcels
                print 'generating model file for Transport1-%s_updated.shp' % requiredDate
                if cleanTargetStep != 0.0:
                    generateOSCOM('./BoatRamps/BoatRamps_GOM_1.shp', './ShapeData/Transport1-%s_updated.shp' % requiredDate, containRadius, operCap, cleanTargetStep, distThreshold, 'data/CUT' + str(cleanTargetStep * 100) + '/OSCOM_%s.lp' % requiredDate)
                if cleanTargetStep != 0.0:
                    gbSolveOSCOM('data/CUT' + str(cleanTargetStep * 100) + '/OSCOM_%s.lp' % requiredDate, 'data/CUT' + str(cleanTargetStep * 100) + '/OSCOM_%s_log.txt' % requiredDate, 'data/CUT' + str(cleanTargetStep * 100) + '/OSCOM_%s_sol.txt' % requiredDate)
                addingCleanedAttribute(requiredDate,cleanTargetStep)


        # PART 3
        # STEP 1
        #Merging all the cleaned files for that cleanup target and converting them to .csv
        #For eg: All cleaned files in CUT95.0 will be merged and converted to .csv format
        fileNamePattern = 'Transport1-'  # + requiredDate #+ '_cleaned'
        #     sys.path.append('data/CUT' + str(cleanTargetStep * 100))
        files = glob.glob('data/CUT' + str(cleanTargetStep * 100) + '/' + fileNamePattern + '*_cleaned.dbf')
        print files
        w = shapefile.Writer()
        for f in files:
            r = shapefile.Reader(f)
            w._shapes.extend(r.shapes())
            w.records.extend(r.records())
        w.fields = list(r.fields)
        # Saving the merged files as a .dbf file. Now this has to be converted to a CSV
        w.save(r"data/CUT" + str(cleanTargetStep * 100) + "/" + "finalFile"+str(cleanTargetStep * 100)+".dbf")

        # Converting the merged .dbf file to a CSV file
        filename = "data/CUT" + str(cleanTargetStep * 100) + "/" + "finalFile"+str(cleanTargetStep * 100)+".dbf"
        if filename.endswith('.dbf'):
            print ("Converting %s to csv" % filename)
            csv_fn = filename[:-4] + ".csv"
            with open(csv_fn, 'wb') as csvfile:
                in_db = dbf.Dbf(filename)
                out_csv = csv.writer(csvfile)
                names = []
                for field in in_db.header.fields:
                    names.append(field.name)
                out_csv.writerow(names)
                for rec in in_db:
                    out_csv.writerow(rec.fieldData)
                in_db.close()
                print ("Done...")
        else:
            print ("Filename does not end with .dbf")
        # A finalFile with the corresponding cleanup target is generated at the end of this PART 3

        # PART 3
        # STEP 2
        # Getting only the required columns from the csv files. Helps us to reduce the file size by almost 70-80%
        print ("Generating finalFile" + str(cleanTargetStep * 100) + " with only the Required Columns")
        filename = "data/CUT" + str(cleanTargetStep * 100) + "finalFile"+str(cleanTargetStep * 100)+".csv"
        f_in_csv = open(filename, 'rb')
        next(f_in_csv)
        f_out_csv = open(filename[:-4] + ".csv", 'wb')
        in_csv = csv.reader(f_in_csv)
        with f_out_csv as out_csv:
            fieldnames = ['CURR_TIME','STATUS','LONGITUDE','LATITUDE','CLEANED']
            writer = csv.DictWriter(out_csv, fieldnames=fieldnames)
            writer.writeheader()
            for row in in_csv:
                writer.writerow({'CURR_TIME': row[0], 'STATUS': row[12], 'LONGITUDE' : row[16], 'LATITUDE' : row[17], 'CLEANED' : row[40]})  # 12th column is STATUS in finalFileXX.csv
        out_csv.close


        # PART 4
        # The list of activated boat ramps is taken from the solution file for each day of this particular cleanup target running here
        # In other words, if the current cleanup target is 95%, we want to find the list of all the boat ramps activated for each day of the simulation for 95% cleanup alone
        # and in the next iteration, the same is computed for other cleanup targets
        # Generating the required csv for highlighting the BOAT RAMPS
        # Again, the values of the parsedDate might have been changed in the previous PART's and hence we create new variables here
        if cleanTargetStep != 0.0:
            parsedDate2 = str(parse(startDate))
            parsedDate2 = parsedDate2[0:-6]
            modelRuntime2 = int(modelRuntimeOriginal[0:2])

            rf = open("data/CUT" + str(cleanTargetStep * 100) + "/" + "ResultBoatRampDayWise"+ str(cleanTargetStep * 100) +".csv", "w")
            rf.write("date,boatRampId");
            rf.write("\n");
            for i in range(1, modelRuntime2 + 1):
                requiredDate = str(datetime.datetime.strptime(parsedDate2, '%Y-%m-%d %H:%M:%S') + datetime.timedelta(days=i))
                tempDate = requiredDate
                tempDate = string.replace(tempDate, " 00:00:00", "")
                print tempDate
                requiredDate = string.replace(requiredDate, "-", "")
                requiredDate = string.replace(requiredDate, " ", "T")
                requiredDate = string.replace(requiredDate, ":", "")

                fileNamePattern = "data/CUT" + str(cleanTargetStep * 100) + "/" + "OSCOM_" + requiredDate + "_sol.txt"
                # sys.path.append('./ShapeData')
                # sys.path.append('TestData2')
                currentSolFile = open(fileNamePattern)
                for solLine in currentSolFile.readlines(): # we parse the solution file and get the required data
                    if solLine.__contains__('x'):
                        boatRampId, parcelNum = solLine[10:-1].split("j")
                        rf.write("%s,%f" % (tempDate, int(boatRampId[1:])))
                        rf.write("\n");
            rf.close()

            # The above file generated in PART 4 may contain duplicates which we want to eliminate
            # Removing duplicate entries from ResultBoatRampDayWise[CUT Number].csv and renaming it to ResultBoatRampDayWise[CUT Number]_unique.csv
            boatRampsHighlightFile = open("data/CUT" + str(cleanTargetStep * 100) + "/" + "ResultBoatRampDayWise"+ str(cleanTargetStep * 100) +".csv", "r")
            boatRampsHighlightFileUnique = open("data/CUT" + str(cleanTargetStep * 100) + "/" + "ResultBoatRampDayWise_Unique"+ str(cleanTargetStep * 100) +".csv", "w")
            with boatRampsHighlightFile as inputFile, boatRampsHighlightFileUnique as outputFile:
                uniqueMaker = set()
            for line in inputFile:
                if line not in uniqueMaker:
                    uniqueMaker.add(line)
                    outputFile.write(line)
            boatRampsHighlightFile.close()
            boatRampsHighlightFileUnique.close()

        # PART 5
        # Now, we have seen that the geneated final files don't have a projection file which we'll be needing to perform the spatial join
        # For this purpose, we are generating .prj files for the Final Files generated in this cleanup target
        prj_file = open("./ShapeData/Transport1-"+ formatizeTempDate(parsedDate)+".prj", "r") #We randomly choose one .prj for this as all the .prj files have the same content
        for line in prj_file:
            print line
            with open("data/CUT" + str(cleanTargetStep * 100) + "/finalFile" + str(cleanTargetStep * 100) + ".prj", "w") as prj_outputFile:
                prj_outputFile.write(line)
                prj_outputFile.close()

        prj_file.close()

        # PART 6
        # An inner spatial join happens between the final file generated and the impact grid shape file here
        # STEP 1
        # POLYGONS
        fp = "./ImpactGrid/Impact_Grid_proj.shp"  # Reading Polygon data
        pop = gpd.read_file(fp)

        # POINTS
        fp2 = "data/CUT" + str(cleanTargetStep * 100) + "/finalFile" + str(cleanTargetStep * 100) + ".shp"  # Reading points data
        pop2 = gpd.read_file(fp2)
        print pop.crs
        print pop2.crs

        if pop.crs == pop2.crs:
            print "true"
        else:
            print "false"

        join = gpd.sjoin(pop, pop2, how="inner", op="contains")

        if join.empty:  # we do not have a beaching happening all the times in all the simulations. Hence, we first check if the join is empty or not
            print "empty data, no overlapping present for CUT" + str(
                cleanTargetStep * 100)  # If there is no overlapping between points  and polygons or in other words, if
            # there is no oil under any grid cell at any point of time in the simulation, we print an error message
        else:
            print "join happening"
            outfp = "SpatialJoinFiles/SJOilGrid" + str(cleanTargetStep * 100) + ".shp"
            join.to_file(outfp)
            print "Join Completed"

            # Pre-Processing the DBF for IMPACT GRID Coloring

        ############################################
        # STEP 2
        # Here, we remove all the rows which have been cleaned because we only want to know how much uncleaned oil is present under each grid cell
        rowsToBeRemoved = []
        print 'Removing cleaned rows from SJOilGrid%s.shp' % str(cleanTargetStep * 100)
        r2 = shapefile.Reader("SpatialJoinFiles/SJOilGrid" + str(cleanTargetStep * 100) + ".shp")
        allFields = r2.fields

        i = 0
        cleanedFieldNumber = 0
        for eachField in allFields:
            if eachField[0] == 'CLEANED':
                cleanedFieldNumber = i
            else:
                i += 1
        j = 0
        statusFieldNumber = 0
        for eachField in allFields:
            if eachField[0] == 'STATUS':
                statusFieldNumber = j
            else:
                j += 1

        for rec in r2.records():
            if rec[cleanedFieldNumber - 1] == '1':
                if rec[statusFieldNumber - 1] != 'beached':
                    rowsToBeRemoved.append(rec)

        rowsToBeRemoved.append(None)

        wf = shapefile.Writer(r2.shapeType)

        wf.fields = list(r2.fields)

        i = 0
        for rec in r2.records():
            if rec[cleanedFieldNumber - 1] == '0':
                wf.records.append(rec)
            else:
                i += 1
        wf._shapes.extend(r2.shapes())
        # We rename the file which has only the list of uncleaned parcels with the suffix '_Uncleaned'
        wf.save("SpatialJoinFiles/SJOilGrid" + str(cleanTargetStep * 100) + "_Uncleaned.shp")
        ############################################


        # STEP 3
        # Converting the DBF into CSV
        filename = "SpatialJoinFiles/SJOilGrid" + str(cleanTargetStep * 100) + "_Uncleaned.dbf"
        if filename.endswith('.dbf'):
            print ("Converting %s to csv" % filename)
            csv_fn = filename[:-4] + ".csv"
            with open(csv_fn, 'wb') as csvfile:
                in_db = dbf.Dbf(filename)
                out_csv = csv.writer(csvfile)
                names = []
                for field in in_db.header.fields:
                    names.append(field.name)
                out_csv.writerow(names)
                for rec in in_db:
                    out_csv.writerow(rec.fieldData)
                in_db.close()
                print ("Done...")
        else:
            print ("Filename does not end with .dbf")
        csvfile.close

        # STEP 4
        # Getting the Required Columns CSV file and changing the header to "Polygon_ID", "CURR_TIME"
        print ("Generating SJOilGrid" + str(cleanTargetStep * 100) + "_Uncleaned_RequiredColumns.csv")
        filename = "SpatialJoinFiles/SJOilGrid" + str(cleanTargetStep * 100) + "_Uncleaned.csv"
        f_in_csv = open(filename, 'rb')
        next(f_in_csv)
        f_out_csv = open(filename[:-4] + "_RequiredColumns.csv", 'wb')
        in_csv = csv.reader(f_in_csv)
        with f_out_csv as out_csv:
            fieldnames = ['Polygon_ID', 'CURR_TIME']
            writer = csv.DictWriter(out_csv, fieldnames=fieldnames)
            writer.writeheader()
            for row in in_csv:
                writer.writerow({'Polygon_ID': row[0], 'CURR_TIME': row[51]})  # 51st column is CURR_TIME
        out_csv.close

        # STEP 5
        # Counting the number of occurrences of each row in the entire dataset and writing them to a new file RequiredColumns_Count
        print ("Generating SJOilGrid" + str(cleanTargetStep * 100) + "_Uncleaned_RequiredColumns_Count.csv")
        filename2 = "SpatialJoinFiles/SJOilGrid" + str(cleanTargetStep * 100) + "_Uncleaned_RequiredColumns.csv"
        requiredColumnsCsv = open(filename2, 'rb')
        next(requiredColumnsCsv)
        dict_csv = csv.reader(requiredColumnsCsv)
        entireData = []
        freq = []
        for row in dict_csv:
            entireData.append(row)

        with open(filename2[:-4] + "_Count.csv", 'wb') as csvFinalCountFile:
            writer = csv.writer(csvFinalCountFile)
            writer.writerow(['Polygon_ID', 'CURR_TIME', 'Count'])
            for row in entireData:
                writer.writerow([row[0], row[1], entireData.count(row)])
        csvFinalCountFile.close

        # STEP 6
        # Removing the duplicate entries from the Required Columns Count File
        print ("Generating SJOilGrid" + str(cleanTargetStep * 100) + "_Uncleaned_RequiredColumns_Count_Unique.csv")
        with open("SpatialJoinFiles/SJOilGrid" + str(cleanTargetStep * 100) + "_Uncleaned_RequiredColumns_Count.csv",
                  'r') as inputFile, open("SpatialJoinFiles/SJOilGrid" + str(
                    cleanTargetStep * 100) + "_Uncleaned_RequiredColumns_Count_Unique.csv", 'w') as outputFile:
            uniqueMaker = set()
            for line in inputFile:
                if line not in uniqueMaker:
                    uniqueMaker.add(line)
                    outputFile.write(line)
        outputFile.close

        # STEP 7
        # Here, we consider only the latest time of the parcels in the polygons and eliminate the rows with earlier times during the day
        filename2 = "SpatialJoinFiles/SJOilGrid" + str(cleanTargetStep * 100) + "_Uncleaned_RequiredColumns_Count_Unique.csv"
        requiredColumnsCsv = open(filename2, 'rb')
        requiredColumnsCsv2 = csv.DictReader(requiredColumnsCsv, delimiter=',')

        entireData = []
        requiredColumnsCsv2.next()

        result = {}
        outputAr = []
        for row in requiredColumnsCsv2:
            if row not in outputAr:
                el = row['Polygon_ID'] + "," + row['CURR_TIME'][:11]
                el2 = row['Polygon_ID'] + "," + row['CURR_TIME'] + "," + row['Count']
                if not any(el in xs for xs in outputAr):
                    outputAr.append(row['Polygon_ID'] + "," + row['CURR_TIME'] + "," + row['Count'])
                else:
                    matching = [s for s in outputAr if el in s]
                    currElIndex = outputAr.index(matching[0])
                    currEl = outputAr[currElIndex]
                    currInsertedDate = currEl.split(',')[1]
                    currInsertedCount = currEl.split(',')[2]
                    newDate = el2.split(',')[1]
                    newCount = el2.split(',')[2]
                    insertedDate_Time = datetime.strptime(currInsertedDate, '%Y-%b-%d %H:%M:%S')
                    newDate_Time = datetime.strptime(newDate, '%Y-%b-%d %H:%M:%S')
                    if (newDate > currInsertedDate):
                        outputAr[currElIndex] = el2
                    else:
                        outputAr[currElIndex] = currEl

        print len(outputAr)
        requiredColumnsCsv.close()

        outputFilename = "SpatialJoinFiles/SJOilGrid" + str(cleanTargetStep * 100) + "Uncleaned_RequiredColumns_Count_Unique_LatestCount.csv"
        requiredColumnsCsvLatest = open(outputFilename, 'wb')
        requiredColumnsCsvLatest.write('Polygon_ID,CURR_TIME,Count')
        requiredColumnsCsvLatest.write("\n")
        for everyRow in outputAr:
            requiredColumnsCsvLatest.write(everyRow)
            requiredColumnsCsvLatest.write("\n")
        requiredColumnsCsvLatest.close()