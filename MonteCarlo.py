import numpy as np
from arcpy import env
from arcpy.sa import *
from arcpy.da import *


fishnet_File = arcpy.GetParameterAsText(0)
attFields = arcpy.GetParameterAsText(1)
n = arcpy.GetParameterAsText(2)
t = arcpy.GetParameterAsText(3)
sampleNum = arcpy.GetParameterAsText(4)

n = int(n)
sampleNum = int (sampleNum)

#fishnet_File = open("C:\\Temp\\AllRun_bbl_final.csv", "r")
#fishnet_File = ("C:\\Temp\\Working_Layers\\AllRun_bbl_final.shp")
#attFields = ("Sum_Crude_", "Sum_Crud_1","Sum_Crud_2","Sum_Crud_3", "Sum_Crud_4", "Sum_Crud_5", "Sum_Crud_6", 
            #"Sum_Crud_7","Sum_Crud_8","Sum_Crud_9","Sum_Cru_10","Sum_Cru_11","Sum_Cru_12","Sum_Cru_13","Sum_Cru_14","Sum_Cru_15","Sum_Cru_16","Sum_Cru_17","Sum_Cru_18","Sum_Cru_19")


#addField = ("MCMean", "StdErr", "CISize", "CI")
#theLine = fishnet_File.readline()
#TheWriteFile=open("C:\\Temp\\testing.txt","w")
#TheWriteFile.write("ID"+"\t")
#TheWriteFile.write("MCMean"+"\t")
#TheWriteFile.write("StdErr"+"\t")
#TheWriteFile.write("CISize"+"\t")
#TheWriteFile.write("CI"+"\n")
#TheWriteFile.write("Significant?"+"\n")
#t = "b"
#n = 500

theFields = attFields.split(";")

lstFields = arcpy.ListFields(fishnet_File, "*MCMean")

arcpy.AddMessage("Checking if fields exist...")

fieldCount = len(lstFields)

#print lstFields

if fieldCount == 1:
    
    arcpy.AddMessage("Fields exist, beginning resample procedure...")
    
    pass

else:
    
    arcpy.AddMessage("Creating new fields...")
    
    arcpy.AddField_management(in_table=fishnet_File, field_name="MCMean", field_type="FLOAT", 
                                  
                                  field_is_nullable="NULLABLE")
    
    arcpy.AddField_management(in_table=fishnet_File, field_name="StdErr", field_type="FLOAT", 
                                   
                                  field_is_nullable="NULLABLE")
    
    arcpy.AddField_management(in_table=fishnet_File, field_name="CISize", field_type="FLOAT", 
                                 
                                  field_is_nullable="NULLABLE")
    
    arcpy.AddField_management(in_table=fishnet_File, field_name="CI", field_type="STRING", 
                                  field_precision=5,
                                  field_length= 20,
                                  field_is_nullable="NULLABLE")
    
 
cursor = arcpy.UpdateCursor(fishnet_File)
#cursor2 = arcpy.da.updateCursor(fishnet_File)

for row in cursor:
    
    cellArray = []
    for attribute in theFields:
        #arcpy.AddMessage(theFelds)
        val =  row.getValue(attribute)
        #ID = row.getValue("FID")
        numValue = float(val)
        print numValue
        cellArray.append(numValue)
    i = 0
    meanArray = []
    while i < n :
        sample = np.random.choice(cellArray, sampleNum, replace = True)
        
                        
        mean = np.mean(sample)
        #mean = statistics.mean(sample)
        meanArray.append(mean)
        counter = i
        print (counter)
        i +=1   
        
    mc = np.mean(meanArray)
    mcMean = float(mc)
    arraySum = sum(meanArray)        
       
    if arraySum != 0: 
        sigma = np.std(meanArray)    
        
        #90% confidence interval
        if t == "a":
            ciPositive = mcMean + (1.645 * sigma)
            ciNegative = mcMean - (1.645 * sigma)
            
        #95% confidence interval
        if t == "b":
            ciPositive = mcMean + (1.96 * sigma)
            ciNegative = mcMean - (1.96 * sigma)
            
        #99% confidence interval
        if t == "c":
            ciPositive = mcMean + (2.576 * sigma)
            ciNegative = mcMean - (2.576 * sigma) 
            
        if ciNegative < 0:
            ciNegative = 0
            
        else: 
            pass        
        intciNegative = format(ciNegative, '.2f')
        intciPositive = format(ciPositive, '.2f')
        
        print intciNegative
        
        ci = (intciNegative)+","+(intciPositive)
        
        
        ciSize = abs(ciNegative - ciPositive)
        print ciSize
    else:
        ci = 0.00
        sig = 0.00
        sigma = 0.00
        ciSize = 0.00
        
        tstat = "n/a"

    print (mcMean)
    print (ci)
    print ciSize
    
    
    row.setValue ("MCMean", mcMean)
    cursor.updateRow(row)
    row.setValue ("StdErr", sigma)
    cursor.updateRow(row)
    row.setValue ("CISize", ciSize)
    cursor.updateRow(row)
    row.setValue ("CI", ci)
    
    cursor.updateRow(row)
    
    #TheWriteFile.write(format(ID)+"\t")
    #TheWriteFile.write(format(mcMean)+"\t")
    #TheWriteFile.write(format(sigma)+"\t")
    #TheWriteFile.write(format(ciSize)+"\t")
    #TheWriteFile.write(format(ci)+"\n")    
    
    
    print format(ciSize)




#for row in fishnet_File:
    #print (row[0:])
    #line = row.rstrip()
    #values = line.split(",")
    #ID = values [0]
    #print (ID)
    
    #cellArray = []
    #for value in values[1:]:
        #numValue = float(value)
        #print (numValue)
        #cellArray.append (numValue)
    #i = 0 
    #meanArray = []
    #while i <= 1000 :      
        #sample = np.random.choice(cellArray, 10, replace = True)
                
        #mean = np.mean(sample)
        ##mean = statistics.mean(sample)
        #meanArray.append(mean)
        #counter = i
        #print (counter)
        #i +=1 
    
    #mcMean = np.mean(meanArray)
    #arraySum = sum(meanArray)
    
    #print arraySum
    
    #if arraySum != 0: 
        #sigma = np.std(meanArray)
    
        ##plt.hist(meanArray, 20, histtype='step', normed=True, linewidth=1, facecolor = 'green')
        ##plt.axis([0, 50, 0, 100])
        ##plt.show()
        ## need to have seperate checks for each standard deviation. 
        
        ##90% confidence interval
        #if t == "a":
            #ciPositive = mcMean + (1.645 * sigma)
            #ciNegative = mcMean - (1.645 * sigma)
            
        ##95% confidence interval
        #if t == "b":
            #ciPositive = mcMean + (1.96 * sigma)
            #ciNegative = mcMean - (1.96 * sigma)
            
        ##99% confidence interval
        #if t == "c":
            #ciPositive = mcMean + (2.576 * sigma)
            #ciNegative = mcMean - (2.576 * sigma)    
            
            
            
            
            
        #ci = format(ciNegative)+","+format(ciPositive)
        
        ##print ci
        ##tstat = stats.ttest_1samp(meanArray, 0.0)
    ##Check the distribution of values by uncommenting this code.  
    ##if arraySum > 25000:
        ##plt.hist(meanArray, 10, histtype='step', normed=True, linewidth=1, color = 'green')
        ###plt.axis([0, 15, 0, 20])
        ##plt.show()    
    #else:
        #ci = 0
        #sig = 0
        #sigma = 0
        
        #tstat = "n/a"
    
    #print (mcMean)
    #print (ci)
    
    
    #TheWriteFile.write(format(ID)+"\t")
    #TheWriteFile.write(format(mcMean)+"\t")
    #TheWriteFile.write(format(sigma)+"\t")
    #TheWriteFile.write(format(ci)+"\n")
    ##TheWriteFile.write(format(sig)+"\n")
    
    
    
        
    


        

        
    
    
    
    



