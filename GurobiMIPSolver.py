import gurobipy as gb

def gbSolveOSCOM(modelFile, logFil, resultFil):
    mod=gb.read(modelFile)
    mod.reset()
    mod.setParam('LogFile', logFil)
    mod.setParam('MIPGap', 0.0)
    mod.setParam('TimeLimit', 20000)
    #mod.setParam('MIPFocus', 2.0)
    mod.optimize()
    rf=open(resultFil, 'w')
    xSol = []
    for deVar in mod.getVars():
        if deVar.VarName.startswith('u'):
            if deVar.X>0.99:
                rf.write("%f, %s" %(deVar.X, deVar.VarName))
                rf.write("\n")  
                xSol.append(int(deVar.VarName.split('u')[1]))
        else:
            if deVar.X>0.00:
                rf.write("%f, %s" %(deVar.X, deVar.VarName))
                rf.write("\n") 
            if deVar.VarName.startswith('z1'):
                z1 = deVar.X
                
    return [z1, mod.NumConstrs, mod.NumVars, mod.Runtime, mod.ObjVal, xSol]

if __name__=='__main__':
    gbSolveOSCOM('OSCOM_0602.lp', 'OSCOM_0602_log.txt', 'OSCOM_0602_sol.txt')