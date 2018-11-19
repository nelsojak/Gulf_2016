import shapelib
import dbflib
from shapely.geometry import Point, Polygon, LineString
from numpy.random import randint, choice
from GurobiSolver import gbSolveEBAM
#from shapely.ops import unary_union
#from shapely.geos import TopologicalError


def writeShp(geoList, outFilePath, geoType):
    if not (geoType in ["Point", "Ptgon", "Line"]):
        print "The output geometry type should be Point, Ptgon, or Line"
        return    

    if geoType=="Point":
        geoT=shapelib.SHPT_POINT
    elif geoType=="Ptgon":
        geoT=shapelib.SHPT_POLYGON
    else:
        geoT=shapelib.SHPT_ARC            
    
    outShp = shapelib.create(outFilePath, geoT)
    outDbf = dbflib.create(outFilePath.split('.')[0]+'.dbf')   
    outDbf.add_field("ID", dbflib.FTInteger, 100, 0)        
         
    for j in range(len(geoList)):
        recordDict={"ID":j}
        if geoType=="Polygon":
            if geoList[j].geom_type == 'Polygon':
                vert = [list(geoList[j].exterior.coords)]
                for interi in geoList[j].interiors:
                    vert.append(list(interi.coords))
            #print vert            
        else:
            vert = [list(geoList[j].coords)]
        obj = shapelib.SHPObject(geoT, -1, vert)    
        outShp.write_object(-1, obj)
        outDbf.write_record(j, recordDict)
    
    print "%d records, %d fields" % (outDbf.record_count(), outDbf.field_count())  
    
def createPolygonFast(filePath):  
    shpList=[]
    shp=shapelib.ShapeFile(filePath)
    dbf=dbflib.DBFFile(filePath.split('.')[0]+'.dbf')
    
    for j in range(dbf.record_count()):        
        inter = shp.read_object(j).vertices()[1:]
        if inter:
            geo = Polygon(shp.read_object(j).vertices()[0], inter)
        else:
            geo = Polygon(tuple(shp.read_object(j).vertices()[0]))
            
        shpList.append(geo)   
        
    return shpList

def createPolygonFastNoInterior(filePath):  
    shpList=[]
    shp=shapelib.ShapeFile(filePath)
    dbf=dbflib.DBFFile(filePath.split('.')[0]+'.dbf')
    
    for j in range(dbf.record_count()):        
        inter = shp.read_object(j).vertices()[1:]

        geo = Polygon(tuple(shp.read_object(j).vertices()[0]))
            
        shpList.append(geo.buffer(0))   
        
    return shpList

def generateCoverageDictForPoly(demList, siteBufferList):
    coveredDict={}
    for idem, dem in enumerate(demList):
        coveredDict[idem]=[]

    for isite, site in enumerate(siteBufferList):
        for idem, dem in enumerate(demList):
            if site.contains(dem):
                coveredDict[idem].append(isite)
                
    return coveredDict

def createPointCoordFast(filePath):  
    shpList=[]
    shp=shapelib.ShapeFile(filePath)
    dbf=dbflib.DBFFile(filePath.split('.')[0]+'.dbf')
    for j in range(dbf.record_count()):
        geo=shp.read_object(j).vertices()[0]
        shpList.append(geo)         
 
    return shpList

def createPointFast(filePath):  
    shpList=[]
    shp=shapelib.ShapeFile(filePath)
    dbf=dbflib.DBFFile(filePath.split('.')[0]+'.dbf')
    for j in range(dbf.record_count()):
        geo=Point(tuple(shp.read_object(j).vertices()[0]))
        shpList.append(geo)        
 
    return shpList

def createPointBufferFast(filePath, bufDist):  
    bufList=[]
    shp=shapelib.ShapeFile(filePath)
    dbf=dbflib.DBFFile(filePath.split('.')[0]+'.dbf')

    for j in range(dbf.record_count()):
        geo=Point(tuple(shp.read_object(j).vertices()[0])).buffer(bufDist)
        bufList.append(geo)         
 
    return bufList

def generateFullCoverageDict(demCoordsList, siteCoordsList, radius): 
    coveredDict={}
        
    tree = KDTree(siteCoordsList)
    neighbors = tree.query_ball_point(demCoordsList, radius)
    
    for dem in range(len(demCoordsList)):
        coveredDict[dem]=neighbors[dem]
        
    return coveredDict

def createMCLPModel(coveredDict, siteList, pFac, outputFilePath):
    outputFile=open(outputFilePath, 'w')
    outputFile.write('Maximize')
    outputFile.write('\n')
    demandList=coveredDict.keys()
    
    varList = []  
       
    for s in range(len(demandList)):
        varList.append('y%s' %(s,))
        
        outputFile.write('y%s' %(s,))
        if s != (len(demandList)-1):
            outputFile.write(' +')
        else:
            outputFile.write('\n')
            outputFile.write(' ')
    
    outputFile.write('\n')
    outputFile.write('Subject To')
    outputFile.write('\n')
    j=1
    for k, v in coveredDict.items():
        outputFile.write(' CV%s: ' %(k, ))
        for ls in range(len(v)):
            outputFile.write('x%s' %(v[ls], ))
            if ls != (len(v)-1):
                outputFile.write(' + ')
            else:
                outputFile.write(' - y%s >= 0' %(k, ))
        outputFile.write('\n')
        j=j+1 
        
    outputFile.write(' PF: ')    
    for s in range(len(siteList)):
        varList.append('x%s' %(s,))     
        
        outputFile.write(' x%s' %(s,))
        if s != (len(siteList)-1):
            outputFile.write(' +')
        else:
            outputFile.write(' = %d \n' %(pFac, ))
            outputFile.write(' ')  
            
    outputFile.write('Binary')
    outputFile.write('\n')
    
    for i, vv in enumerate(varList):
        outputFile.write(' %s' %(vv, ))
        
        if i%11==0:
            outputFile.write('\n')
            outputFile.write(' ')        
            
    outputFile.write('\n')    
    outputFile.write('End')
    
def generateBound(demCoordsList, siteCoordsList, pFac, radius, lpPtFile):    
    PtCoveredDict=generateFullCoverageDict(demCoordsList, siteCoordsList, radius)   
    
    if type(pFac)==type([]):
        modResults = []
        for pf in pFac:
            createMCLPModel(PtCoveredDict, siteCoordsList, pf, lpPtFile)
            modResult=gbSolve(lpPtFile, lpPtFile.split('.')[0] + '_%d' %(pf,) + '_log.txt', lpPtFile.split('.')[0] + '_%d' %(pf,) + '_sol.txt')  
            modResults.append(modResult)
        return modResults
    else:
        createMCLPModel(PtCoveredDict, siteCoordsList, pFac, lpPtFile)
        modResult=gbSolve(lpPtFile, lpPtFile.split('.')[0] + '_%d' %(pFac,) + '_log.txt', lpPtFile.split('.')[0] + '_%d' %(pFac,) + '_sol.txt')  
        return modResult  
    
def calculateShoreLength(gridFilePath, shoreFilePath, outFilePath):  
    gridShp = shapelib.ShapeFile(gridFilePath)
    gridDbf = dbflib.DBFFile(gridFilePath.split('.')[0]+'.dbf')
    shoreShp = shapelib.ShapeFile(shoreFilePath)
    
    outShp = shapelib.create(outFilePath, shapelib.SHPT_POLYGON)
    outDbf = dbflib.create(outFilePath.split('.')[0]+'.dbf')   
    outDbf.add_field("ID", dbflib.FTInteger, 10, 0) 
    outDbf.add_field("Impact", dbflib.FTDouble, 30, 6)
    outDbf.add_field("Length", dbflib.FTDouble, 30, 6)
    
    inter = shoreShp.read_object(0).vertices()[1:]
    if inter:
        shoreGeo = Polygon(shoreShp.read_object(0).vertices()[0], inter).boundary
    else:
        shoreGeo = Polygon(tuple(shoreShp.read_object(0).vertices()[0])).boundary

    
    for j in range(gridDbf.record_count()): 
        gridObj = gridShp.read_object(j)
        gridGeo = Polygon(tuple(gridObj.vertices()[0]))
        
        shoreLength = gridGeo.intersection(shoreGeo).length
        recordDict = gridDbf.read_record(j)
        newDict = [j, recordDict["Impact"], shoreLength]
        outShp.write_object(-1, gridObj)
        outDbf.write_record(j, newDict)   

def simulateRampCapacity(rampFilePath, outFilePath):
    rampShp = shapelib.ShapeFile(rampFilePath)
    rampDbf = dbflib.DBFFile(rampFilePath.split('.')[0]+'.dbf')
    
    outShp = shapelib.create(outFilePath, shapelib.SHPT_POINT)
    outDbf = dbflib.create(outFilePath.split('.')[0]+'.dbf')   
    outDbf.add_field("ID", dbflib.FTInteger, 10, 0) 
    outDbf.add_field("EBCap", dbflib.FTInteger, 30, 0)
    outDbf.add_field("VesCap", dbflib.FTInteger, 10, 0)
    
    tn = rampDbf.record_count()
    ebCap = randint(500, high=5001, size=tn)
    vesCap = choice(6, tn, p=[0.5,0.2,0.1,0.1,0.05,0.05])
    
    for j in range(tn): 
        rampObj = rampShp.read_object(j)
        recordDict = rampDbf.read_record(j)
        
        newDict = [j, ebCap[j], vesCap[j]]
        outShp.write_object(-1, rampObj)
        outDbf.write_record(j, newDict)      
    
def generatEBAMInputs(rampFilePath, gridFilePath, speed, hitDay):
    rampShp = shapelib.ShapeFile(rampFilePath)
    rampDbf = dbflib.DBFFile(rampFilePath.split('.')[0]+'.dbf')    
    gridShp = shapelib.ShapeFile(gridFilePath)
    gridDbf = dbflib.DBFFile(gridFilePath.split('.')[0]+'.dbf') 
    
    ebCap = []
    rampGeoList = []
    cdDict = {}
    tn = rampDbf.record_count()    
    for j in range(tn): 
        rampObj = rampShp.read_object(j)
        rampGeo = Point(tuple(rampObj.vertices()[0]))
        rampGeoList.append(rampGeo)
        
        recordDict = rampDbf.read_record(j)
        ebCap.append(recordDict['EBCap_Mete'])
        cdDict[j] = []
    
    distDict = {}
    coverDict = {}
    impactList = []
    needBoomList = []
    for j in range(gridDbf.record_count()): 
        gridObj = gridShp.read_object(j)
        gridGeo = Polygon(tuple(gridObj.vertices()[0]))
        recordDict = gridDbf.read_record(j)
        
        impactList.append(recordDict['Impact'])
        needBoomList.append(recordDict['Length'])
        coverDict[j] = []
        
        for i in range(tn):
            dist = rampGeoList[i].distance(gridGeo)            
            hours = dist / speed
            
            if hours <= hitDay * 24:
                coverDict[j].append(i)
                cdDict[i].append(j)
                distDict[(i,j)] = dist
            
    return [ebCap, impactList, needBoomList, distDict, coverDict, cdDict]      
            

def generateEBAMWeigth(rampFile, gridFilePath, speed, hitDay, weight, outFilePath):
    ebCap, impactList, needBoomList, distDict, coverDict, cdDict = generatEBAMInputs(
                                                                            rampFile, 
                                                                            gridFilePath, 
                                                                            speed, 
                                                                            hitDay)
    outputFile=open(outFilePath, 'w')
        
    outputFile.write('Minimize %f z1 + %f z2' %(weight*410, 1-weight))
    outputFile.write('\n')
    outputFile.write('Subject To')
    outputFile.write('\n')  
    
    varList = [] 
    
    minImpact = min(impactList)
    maxImpact = max(impactList)
    outputFile.write('obj1: z1')
    for i, impact in enumerate(impactList):
        outputFile.write(' - %f x%d' %((impact-minImpact)/(maxImpact-minImpact), i))
        varList.append('x%d' %(i,))
    outputFile.write(' = 0\n')
    
    outputFile.write('obj11: z3')
    for i, impact in enumerate(impactList):
        outputFile.write(' - %f x%d' %(impact, i))
        varList.append('x%d' %(i,))
    outputFile.write(' = 0\n')
    
    minDist = min(distDict.values())
    maxDist = max(distDict.values())
    outputFile.write('obj2: z2')
    for k, v in distDict.items():
        outputFile.write(' - %f y%dk%d' %((v-minDist)/(maxDist-minDist), k[0], k[1]))
        #varList.append('y%dk%d' %(k[0], k[1]))
    outputFile.write(' = 0\n')
    
    outputFile.write('obj22: z4')
    for k, v in distDict.items():
        outputFile.write(' - %f y%dk%d' %(v, k[0], k[1]))
        #varList.append('y%dk%d' %(k[0], k[1]))
    outputFile.write(' = 0\n') 
    
    for k, v in cdDict.items():
        if len(v) == 0:
            continue
        outputFile.write('cap%d: y%dk%d' %(k, k, v[0]))
        for vv in v[1:]:
            outputFile.write(' + y%dk%d' %(k, vv))
        outputFile.write(' <= %f\n' %(ebCap[k],))

    totalEb = sum(ebCap)
    
    for k, v in coverDict.items():
        if len(v) == 0:
            outputFile.write('pro%d: x%d = 1' %(k,))
        else:
            outputFile.write('pro%d: %f x%d' %(k, totalEb, k))
            for vv in v:
                outputFile.write(' + y%dk%d' %(vv, k))
            outputFile.write(' >= %f\n' %(needBoomList[k],))        

    outputFile.write('Binary')
    outputFile.write('\n')
    
    for i, vv in enumerate(varList):
        outputFile.write(' %s' %(vv, ))
        
        if i%11==0:
            outputFile.write('\n')
            outputFile.write(' ')        
            
    outputFile.write('\n')    
    outputFile.write('End')    
    
def generateEBAMConstraint(rampFile, gridFilePath, speed, hitDay, target, outFilePath):
    ebCap, impactList, needBoomList, distDict, coverDict, cdDict = generatEBAMInputs(
                                                                            rampFile, 
                                                                            gridFilePath, 
                                                                            speed, 
                                                                            hitDay)
    outputFile=open(outFilePath, 'w')
        
    outputFile.write('Minimize z4')
    outputFile.write('\n')
    outputFile.write('Subject To')
    outputFile.write('\n')  
    
    varList = [] 
        
    outputFile.write('obj11: z3')
    for i, impact in enumerate(impactList):
        outputFile.write(' - %f x%d' %(impact, i))
        varList.append('x%d' %(i,))
    outputFile.write(' = 0\n')
    
    outputFile.write('cnst: z3 <= %f\n' %(sum(impactList) * target))
       
    outputFile.write('obj22: z4')
    for k, v in distDict.items():
        outputFile.write(' - %f y%dk%d' %(v, k[0], k[1]))
        #varList.append('y%dk%d' %(k[0], k[1]))
    outputFile.write(' = 0\n') 
    
    for k, v in cdDict.items():
        if len(v) == 0:
            continue
        outputFile.write('cap%d: y%dk%d' %(k, k, v[0]))
        for vv in v[1:]:
            outputFile.write(' + y%dk%d' %(k, vv))
        outputFile.write(' <= %f\n' %(ebCap[k]/1.2,))

    totalEb = sum(ebCap)
    
    for k, v in coverDict.items():
        if len(v) == 0:
            outputFile.write('pro%d: x%d = 1' %(k,))
        else:
            outputFile.write('pro%d: %f x%d' %(k, totalEb, k))
            for vv in v:
                outputFile.write(' + y%dk%d' %(vv, k))
            outputFile.write(' >= %f\n' %(needBoomList[k],))        

    outputFile.write('Binary')
    outputFile.write('\n')
    
    for i, vv in enumerate(varList):
        outputFile.write(' %s' %(vv, ))
        
        if i%11==0:
            outputFile.write('\n')
            outputFile.write(' ')        
            
    outputFile.write('\n')    
    outputFile.write('End')
    
def AddBoomField(gridFilePath, sol, outFilePath):
    gridSHP = shapelib.ShapeFile(gridFilePath)
    gridDBF = dbflib.DBFFile(gridFilePath.split('.')[0] + '.dbf')
    
    outSHP = shapelib.create(outFilePath, shapelib.SHPT_POLYGON)
    outDBF = dbflib.create(outFilePath.split('.')[0]+'.dbf')
    
    for j in range(gridDBF.field_count()):
        #if j == 17:
            #outDBF.add_field(gridDBF.field_info(j)[1], dbflib.FTDouble, 20, 10)
        #else:
            outDBF.add_field(gridDBF.field_info(j)[1], gridDBF.field_info(j)[0], gridDBF.field_info(j)[2], gridDBF.field_info(j)[3])
        
    outDBF.add_field('Boomed', dbflib.FTInteger,5, 0)

    jj = 0
    for j in range(gridDBF.record_count()):
        vert = gridSHP.read_object(j)
        recordDict=gridDBF.read_record(j)  
        
        if j in sol:        
            recordDict['Boomed'] = 1
        else:
            recordDict['Boomed'] = 0

        outSHP.write_object(-1, vert)
        outDBF.write_record(jj, recordDict)
        jj += 1
    
    
        
if __name__=='__main__':   
    speed = 22224
    hitDay = 16
    #weight = 1.0
    resultFile = open('result\\obj.txt', 'w')
    
    #for weight in range(11):
        #generateEBAM('data\\new\\BoatRamps_TXLA_bdry_new.shp', 'data\\new\\ImpactGrid_new.shp', speed, hitDay, weight*0.1, 'result\\EBAM_%d.lp' %(weight))
        #result = gbSolveEBAM('result\\EBAM_%d.lp' %(weight), 'result\\EBAM_%d_log.txt' %(weight), 'result\\EBAM_%d_sol.txt' %(weight))
        #resultFile.write('%f,%f\n' %(result[0], result[1]))
        
    for target in range(10,101,5):
        generateEBAMConstraint('data\\new\\BoatRamps_TXLA_bdry_new.shp', 'data\\new\\ImpactGrid_new.shp', speed, hitDay, target*0.01, 'result\\EBAM_%d.lp' %(target))
        result = gbSolveEBAM('result\\EBAM_%d.lp' %(target), 'result\\EBAM_%d_log.txt' %(target), 'result\\EBAM_%d_sol.txt' %(target))
        AddBoomField('data\\new\\ImpactGrid_new.shp', result[-1], 'result\\ImpactGrid_new_%d.shp' %(target))
        resultFile.write('%f,%f\n' %(result[0], result[1]))    