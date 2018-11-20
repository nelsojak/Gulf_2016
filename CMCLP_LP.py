import shapelib
import dbflib
from shapely.geometry import Point, Polygon, LineString
from numpy.random import random_sample
from GurobiSolver import gbSolveCMCLP, gbSolveMCLP       
                
def generateMCLPInputsGrid(rampFilePath, gridFilePath, distThreshold):
    rampShp = shapelib.ShapeFile(rampFilePath)
    rampDbf = dbflib.DBFFile(rampFilePath.split('.')[0]+'.dbf')    
    gridShp = shapelib.ShapeFile(gridFilePath)
    gridDbf = dbflib.DBFFile(gridFilePath.split('.')[0]+'.dbf') 

    rampGeoList = []
    tn = rampDbf.record_count()    
    for j in range(tn): 
        rampObj = rampShp.read_object(j)
        rampGeo = Point(tuple(rampObj.vertices()[0]))
        rampGeoList.append(rampGeo)
        
        recordDict = rampDbf.read_record(j)

    distDict = {}
    serveDict = {}
    gridLenList = []
    gridSenList = []
    gridGeoList = []
    sn = gridDbf.record_count()

    for j in range(sn): 
        serveDict[j] = []
        gridObj = gridShp.read_object(j)
        gridGeo = Polygon(tuple(gridObj.vertices()[0])).centroid
        gridGeoList.append(gridGeo)
        
        recordDict = gridDbf.read_record(j)        
        gridSenList.append(recordDict['Total_S'])
        
        for i in range(tn):
            dist = rampGeoList[i].distance(gridGeo) 
            if dist <= distThreshold:
                distDict[(i,j)] = dist  
                serveDict[j].append(i)
                
    servedDict = {}
    for i in range(tn):
        servedDict[i] = []
        for k, v in serveDict.items():
            if i in v:
                servedDict[i].append(k)        
            
    print 'done'
    return [gridSenList, serveDict, servedDict]
 
def generateMCLPInputs(rampFilePath, shoreFilePath, distThreshold):
    rampShp = shapelib.ShapeFile(rampFilePath)
    rampDbf = dbflib.DBFFile(rampFilePath.split('.')[0]+'.dbf')    
    shoreShp = shapelib.ShapeFile(shoreFilePath)
    shoreDbf = dbflib.DBFFile(shoreFilePath.split('.')[0]+'.dbf') 
    
    rampGeoList = []
    tn = rampDbf.record_count()    
    for j in range(tn): 
        rampObj = rampShp.read_object(j)
        rampGeo = Point(tuple(rampObj.vertices()[0]))
        rampGeoList.append(rampGeo)
        
        recordDict = rampDbf.read_record(j)

    distDict = {}
    serveDict = {}
    shoreSenList = []
    shoreGeoList = []
    sn = shoreDbf.record_count()

    for j in range(sn): 
        serveDict[j] = []
        shoreObj = shoreShp.read_object(j)
        shoreGeo = LineString(tuple(shoreObj.vertices()[0])).centroid
        shoreGeoList.append(shoreGeo)
        
        recordDict = shoreDbf.read_record(j)        
        shoreSenList.append(recordDict['ESI_1'])
        
        for i in range(tn):
            dist = rampGeoList[i].distance(shoreGeo) 
            if dist <= distThreshold:
                distDict[(i,j)] = dist  
                serveDict[j].append(i)
                
    servedDict = {}
    for i in range(tn):
        servedDict[i] = []
        for k, v in serveDict.items():
            if i in v:
                servedDict[i].append(k)        
            
    print 'done'
    return [shoreSenList, serveDict, servedDict]

def generateMCLP(shoreSenList, serveDict, servedDict, pFac, outputFilePath):        
    outputFile=open(outputFilePath, 'w')
    outputFile.write('Maximize z')
    outputFile.write('\n')

    outputFile.write('Subject To')
    outputFile.write('\n')
    
    varList = []  
    siteList = servedDict.keys()
    
    outputFile.write('obj: z')
    for i, impact in enumerate(shoreSenList):
        varList.append('y%d' %(i,))
        outputFile.write(' - %f y%d' %(impact, i))        
    outputFile.write(' = 0\n')
            
    for k, v in serveDict.items():
        outputFile.write(' CV%s: ' %(k, ))
        if len(v) == 0:
            outputFile.write(' y%s = 0\n' %(k, ))
            continue
        for ils, ls in enumerate(v):
            outputFile.write('x%s' %(ls, ))
            if ils != (len(v)-1):
                outputFile.write(' + ')
            else:
                outputFile.write(' - y%s >= 0' %(k, ))
        outputFile.write('\n')
        
    outputFile.write(' PF: ')    
    for iss, s in enumerate(siteList):
        varList.append('x%s' %(s,))     
        
        outputFile.write(' x%s' %(s,))
        if iss != (len(siteList)-1):
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
    
def generateMCLPGrid(gridSenList, serveDict, servedDict, pFac, outputFilePath):        
    outputFile=open(outputFilePath, 'w')
    outputFile.write('Maximize z')
    outputFile.write('\n')

    outputFile.write('Subject To')
    outputFile.write('\n')
    
    varList = []  
    siteList = servedDict.keys()
    
    outputFile.write('obj: z')
    for i, impact in enumerate(gridSenList):
        varList.append('y%d' %(i,))
        outputFile.write(' - %f y%d' %(impact, i))        
    outputFile.write(' = 0\n')
            
    for k, v in serveDict.items():
        outputFile.write(' CV%s: ' %(k, ))
        if len(v) == 0:
            outputFile.write(' y%s = 0\n' %(k, ))
            continue        
        for ils, ls in enumerate(v):
            outputFile.write('x%s' %(ls, ))
            if ils != (len(v)-1):
                outputFile.write(' + ')
            else:
                outputFile.write(' - y%s >= 0' %(k, ))
        outputFile.write('\n')
        
    outputFile.write(' PF: ')    
    for iss, s in enumerate(siteList):
        varList.append('x%s' %(s,))     
        
        outputFile.write(' x%s' %(s,))
        if iss != (len(siteList)-1):
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

        
        
        
if __name__=='__main__':   
    speed = 22224
    hours = 1
    distThreshold = speed * hours   
    pFac = 44  
     
    shoreSenList, serveDict, servedDict = generateMCLPInputs('data\\cmclp\\Existing_Storage_sites.shp', 'data\\cmclp\\EasternGOM_ESI.shp', distThreshold) 
    generateMCLP(shoreSenList, serveDict, servedDict, pFac, 'result\\MCLP\\MCLP_Existing_%d.lp' %(pFac))
    gbSolveMCLP('result\\MCLP\\MCLP_Existing_%d.lp' %(pFac), 'result\\MCLP\\MCLP_Existing_%d_log.txt' %(pFac), 'result\\MCLP\\MCLP_Existing_%d_sol.txt' %(pFac))
    readSol('result\\MCLP\\MCLP_Existing_%d_sol.txt' %(pFac), 'result\\MCLP\\MCLP_Existing_%d_sol_sel.txt' %(pFac))
    
    gridSenList, serveDict, servedDict = generateMCLPInputsGrid('data\\cmclp\\Existing_Storage_sites.shp', 'data\\cmclp\\Impact_Grid_EasternGOM.shp', distThreshold) 
    generateMCLPGrid(gridSenList, serveDict, servedDict, pFac, 'result\\MCLP\\MCLP_Existing_Grid_%d.lp' %(pFac))
    gbSolveMCLP('result\\MCLP\\MCLP_Existing_Grid_%d.lp' %(pFac), 'result\\MCLP\\MCLP_Existing_Grid_%d_log.txt' %(pFac), 'result\\MCLP\\MCLP_Existing_Grid_%d_sol.txt' %(pFac))
    readSol('result\\MCLP\\MCLP_Existing_Grid_%d_sol.txt' %(pFac), 'result\\MCLP\\MCLP_Existing_Grid_%d_sol_sel.txt' %(pFac))    
    

 



