import shapelib
import dbflib
from shapely.geometry import Point, Polygon, LineString

def generateOSCOMInputs(rampFilePath, spillFilePath, containRadius, distThreshold):
    rampShp = shapelib.ShapeFile(rampFilePath)
    rampDbf = dbflib.DBFFile(rampFilePath.split('.')[0]+'.dbf')    
    spillShp = shapelib.ShapeFile(spillFilePath)
    spillDbf = dbflib.DBFFile(spillFilePath.split('.')[0]+'.dbf') 
    
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
        volumeList.append(recordDict['Gallons'])        
        
        for i in range(tn):
            dist = rampGeoList[i].distance(spillGeo) 
            if dist <= distThreshold:
                distDict[(i,j)] = dist  
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
    vesCapList, volumeList, distDict, serveDict, servedDict, coverDict = generateOSCOMInputs(rampFilePath, 
                                                       spillFilePath,  
                                                       containRadius,
                                                       distThreshold)

    
    outputFile=open(outFilePath, 'w')
        
    outputFile.write('Minimize z1')
    outputFile.write('\n')
    outputFile.write('Subject To')
    outputFile.write('\n')  
    
    xVarList = [] 
    
    outputFile.write('obj: z1')
    for k, v in distDict.items():
        outputFile.write(' - %f x%dj%d' %(v, k[0], k[1]))
        xVarList.append('x%dj%d' %(k[0], k[1]))
    outputFile.write(' = 0\n') 
    
    vn = len(volumeList)
    cn = len(vesCapList)
    
    for i, vesCap in enumerate(vesCapList):        
        if servedDict[i]:
            outputFile.write('cap%d: ' %(i,))
            for jj, j in enumerate(servedDict[i]):
                if jj != (len(servedDict[i]) - 1):
                    outputFile.write('x%dj%d + ' %(i, j))
                else:
                    outputFile.write('x%dj%d <= %d\n' %(i, j, vesCap))
                
    for k, v in coverDict.items():
        if len(v) == 0:
            continue
        outputFile.write('link%d: ' %(k,))
        for ivv, vv in enumerate(v):
            for ii, i in enumerate(serveDict[vv]):
                if ii == (len(serveDict[vv]) - 1) and ivv == (len(v) - 1):
                    outputFile.write('x%dj%d - u%d >= 0\n' %(i, vv, k)) 
                else:
                    outputFile.write('x%dj%d + ' %(i, vv))                  

    uVarList = []
    totalSpill = sum(volumeList)
    outputFile.write('target: ')
    for j, volume in enumerate(volumeList):
        uVarList.append('u%d' %(j,))
        if j != (vn - 1):
            outputFile.write('%f u%d + ' %(volume, j))
        else:
            outputFile.write('%f u%d >= %f\n' %(volume, j, cleanTarget * totalSpill))
            
    
    outputFile.write('Binary')
    outputFile.write('\n')
    
    for i, vv in enumerate(uVarList):
        outputFile.write(' %s' %(vv, ))
        
        if i%11==0:
            outputFile.write('\n')
            outputFile.write(' ')   
            
    outputFile.write('\n')        
    outputFile.write('General')
    outputFile.write('\n')
    
    for i, vv in enumerate(xVarList):
        outputFile.write(' %s' %(vv, ))
        
        if i%11==0:
            outputFile.write('\n')
            outputFile.write(' ')  
    
    outputFile.write('\n')    
    outputFile.write('End')  
            
    
    
if __name__=='__main__':      
    containRadius = 1769
    operCap = 62400
    speed = 22224
    hours = 16
    distThreshold = speed * hours
    cleanTarget = 0.95
    
    date = '0602'

    generateOSCOM('data\\BoatRamps_TXLA_bdry_new_OSCOM.shp', 'data\\Transport_%s_updated.shp' %(date), containRadius, operCap,  
                         cleanTarget, distThreshold, 'OSCOM_%s.lp' %(date))    

    
    
        
