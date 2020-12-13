# NIBEUplink Python Plugin
#
# Author: flopp
#
"""
<plugin key="NIBEUplink" name="NIBE Uplink 0.68" author="flopp" version="0.68" wikilink="https://github.com/flopp999/NIBEUplink-Domoticz" externallink="https://www.nibeuplink.com/">
    <description>
        <h2>NIBE Uplink is used to read data from api.nibeuplink.com</h2><br/>
        <h3>Features</h3>
        <ul style="list-style-type:square">
            <li>..</li>
        </ul>
        <h3>Devices</h3>
        <ul style="list-style-type:square">
            <li>Unit 1x is STATUS</li>
            <li>Unit 2x is CPR_INFO_EP14</li>
            <li>Unit 3x is VENTILATION</li>
            <li>Unit 4x is SYSTEM_1</li>
            <li>Unit 5x is ADDITION</li>
            <li>Unit 6x is SMART_PRICE_ADAPTION</li>
            <li>Unit 7x is SYSTEM_INFO</li>
        </ul>
        <h3>How to get your Access Code?</h3>
        <ul style="list-style-type:square">
            <li>..</li>
        </ul>
        <h3>How to get your System ID?</h3>
        <ul style="list-style-type:square">
            <li>..</li>
        </ul>
        <h3>Configuration</h3>
    </description>
    <params>
        <param field="Username" label="NIBE Uplink Identifier" width="320px" required="true" default="Username"/>
        <param field="Mode2" label="NIBE Uplink Secret" width="350px" required="true" default="Secret"/>
        <param field="Mode3" label="NIBE Refresh Token" width="350px" default="Copy Refresh Token from Log to here" required="true"/>
        <param field="Mode1" label="NIBE Access Code" width="350px" required="true" default="Access Code"/>
        <param field="Address" label="NIBE Callback URL" width="950px" required="true" default="URL"/>
        <param field="Mode4" label="NIBE System ID" width="140px" required="true" default="ID"/>
        <param field="Mode5" label="Electricity Company Charge" width="70px" default="0" required="true"/>
        <param field="Mode6" label="Debug to file (Nibe.log)" width="70px">
            <options>
                <option label="Yes" value="Yes" />
                <option label="No" value="No" default="true" />
            </options>
        </param>
    </params>
</plugin>
"""

import Domoticz

Package = True

try:
    import requests,json,os
except ImportError as e:
    Package = False

try:
    from datetime import datetime
except ImportError as e:
    Package = False

class BasePlugin:
    enabled = False

    def __init__(self):
        self.token = ''
        self.loop = 0
        self.Count = 0
        return

    def onStart(self):
        self.HomeDir = Parameters["HomeFolder"]
        WriteDebug("onStart")
        self.Ident = Parameters["Username"]
        self.URL = Parameters["Address"]
        self.Access = Parameters["Mode1"]
        self.Secret = Parameters["Mode2"]
        self.Refresh = Parameters["Mode3"]
        self.SystemID = Parameters["Mode4"]
        self.Charge = Parameters["Mode5"]

        if len(self.Ident) < 32:
            Domoticz.Log("Username too short")
            self.Ident = CheckFile("Ident")
        else:
            WriteFile("Ident",self.Ident)

        if len(self.URL) < 26:
            Domoticz.Log("URL too short")
            self.URL = CheckFile("URL")
        else:
            WriteFile("URL",self.URL)

        if len(self.Access) < 370:
            Domoticz.Log("Access Code too short")
            self.Access = CheckFile("Access")
        else:
            WriteFile("Access",self.Access)

        if len(self.Secret) < 44:
            Domoticz.Log("Secret too short")
            self.Secret = CheckFile("Secret")
        else:
            WriteFile("Secret",self.Secret)

        if len(self.Refresh) < 270:
            Domoticz.Log("Refresh too short")
            self.Refresh = CheckFile("Refresh")
        else:
            WriteFile("Refresh",self.Refresh)

        if len(self.SystemID) < 4:
            Domoticz.Log("System ID too short")
            self.SystemID = CheckFile("SystemID")
        else:
            WriteFile("SystemID",self.SystemID)

        self.GetCode = Domoticz.Connection(Name="Get Code", Transport="TCP/IP", Protocol="HTTPS", Address="api.nibeuplink.com", Port="443")
        if len(self.Refresh) < 50:
            self.GetCode.Connect() # Get a Token
        self.GetToken = Domoticz.Connection(Name="Get Token", Transport="TCP/IP", Protocol="HTTPS", Address="api.nibeuplink.com", Port="443")
        self.GetData = Domoticz.Connection(Name="Get Data", Transport="TCP/IP", Protocol="HTTPS", Address="api.nibeuplink.com", Port="443")

    def onConnect(self, Connection, Status, Description):
        if CheckInternet() == True:
            if (Status == 0):
                if Connection.Name == ("Get Code"):
                    data = "grant_type=authorization_code"
                    data += "&client_id="+self.Ident
                    data += "&client_secret="+self.Secret
                    data += "&code="+self.Access
                    data += "&redirect_uri="+self.URL
                    data += "&scope=READSYSTEM"
                    headers = { 'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8', 'Host': 'api.nibeuplink.com', 'Authorization': ''}
                    Connection.Send({'Verb':'POST', 'URL': '/oauth/token', 'Headers': headers, 'Data': data})

                if Connection.Name == ("Get Token"):
                    if len(self.Refresh) > 50:
                        self.reftoken = self.Refresh
                    data = "grant_type=refresh_token"
                    data += "&client_id="+self.Ident
                    data += "&client_secret="+self.Secret
                    data += "&refresh_token="+self.reftoken
                    headers = { 'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8', 'Host': 'api.nibeuplink.com', 'Authorization': ''}
                    Connection.Send({'Verb':'POST', 'URL': '/oauth/token', 'Headers': headers, 'Data': data})

                if Connection.Name == ("Get Data"):
                    self.loop = 0
                    for category in ["STATUS", "CPR_INFO_EP14", "VENTILATION", "SYSTEM_1", "ADDITION", "SMART_PRICE_ADAPTION", "SYSTEM_INFO"]:
                        headers = { 'Host': 'api.nibeuplink.com', 'Authorization': 'Bearer '+self.token}
                        Connection.Send({'Verb':'GET', 'URL': '/api/v1/systems/'+self.SystemID+'/serviceinfo/categories/'+category, 'Headers': headers})

    def onMessage(self, Connection, Data):
        Status = int(Data["Status"])

        if (Status == 400):
            Domoticz.Error(str("Something went wrong"))
            if _plugin.GetCode.Connected():
                _plugin.GetCode.Disconnect()
            if _plugin.GetToken.Connected():
                _plugin.GetToken.Disconnect()
            if _plugin.GetData.Connected():
                _plugin.GetData.Disconnect()

        if Connection.Name == ("Get Code"):
            if (Status == 200):
                self.reftoken = Data['Data'].decode('UTF-8')
                self.reftoken = json.loads(self.reftoken)["refresh_token"]
                if len(self.Refresh) < 50:
                    Domoticz.Log("Copy token to Setup->Hardware->NibeUplink->Refresh Token:")
                    Domoticz.Log(str(self.reftoken))
                self.GetCode.Disconnect()
                self.GetToken.Connect()

        if Connection.Name == ("Get Token"):
            if (Status == 200):
                self.token = Data['Data'].decode('UTF-8')
                self.token = json.loads(self.token)["access_token"]
                with open(_plugin.HomeDir+'/NIBEUplink.ini') as jsonfile:
                    data = json.load(jsonfile)
                data["Config"][0]["Access"] = self.token
                with open(_plugin.HomeDir+'/NIBEUplink.ini', 'w') as outfile:
                    json.dump(data, outfile, indent=4)
                self.GetToken.Disconnect()
                self.GetData.Connect()

        if Connection.Name == ("Get Data"):
            if (Status == 200):
                self.data = Data['Data'].decode('UTF-8')
                self.data = json.loads(self.data)
                self.loop += 1
                loop2 = 0
                for each in self.data:
                    loop2 += 1
                    Unit = str(self.loop)+str(loop2)
                    sValue = each["rawValue"]
                    nValue = 0
                    if each["unit"] == "°C" and sValue != -32768:
                        sValue = sValue / 10.0
                    if each["unit"] == "A" and each["title"] != "fuse size":
                        sValue = sValue / 10.0
                    if each["title"] == "set max electrical add.":
                        sValue = sValue / 100.0
                    if each["unit"] == "öre/kWh":
                        sValue = (((sValue / 1000.0) + float(Parameters["Mode5"])) * 1.25)
                    if each["title"] == "time factor":
                        sValue = (sValue / 10.0)
                    if each["title"] == "electrical addition power":
                        sValue = (sValue / 100.0)
                    if each["title"] == "blocked":
                        nValue = int(sValue)
                        if nValue == 0:
                            sValue = "No"
                        else:
                            sValue = "Yes"
                    if each["title"] == "external adjustment":
                        nValue = int(sValue)
                        if nValue == 0:
                            sValue = "No"
                        else:
                            sValue = "Yes"
                    if each["title"] == "status":
                        nValue = int(sValue)
                        if nValue == 30:
                           sValue = "active"
                    if each["title"] == "hot water":
                        nValue = int(sValue)
                        if nValue == 20:
                            sValue = "economy"
                        elif nValue == 30:
                            sValue = "luxury"
                        elif nValue == 1:
                            sValue = "normal"
                    if int(Unit) > 70:
                        sValue = each["displayValue"]

                    UpdateDevice(int(Unit), int(nValue), str(sValue), each["unit"], each["title"], each["parameterId"], each["designation"])
                if self.loop == 7:
                    Domoticz.Log("Updated")
                    self.GetData.Disconnect()

    def onHeartbeat(self):
        self.Count += 1
        if self.Count == 6:
            self.GetToken.Connect()
            WriteDebug("onHeartbeat")
            self.Count = 0

global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def UpdateDevice(ID, nValue, sValue, Unit, Name, PID, Design):
    if (ID in Devices):
        if (Devices[ID].nValue != nValue) or (Devices[ID].sValue != sValue):
            Devices[ID].Update(nValue, str(sValue))
    if (ID not in Devices):
        if sValue == "-32768":
            return
        elif ID == 24:
            Domoticz.Device(Name="compressor "+Name, Unit=ID, TypeName="Temperature", Used=1, Description="ParameterID="+str(PID)+"\nDesignation="+str(Design)).Create()
        elif Unit == "°C" and ID !=24:
            Domoticz.Device(Name=Name, Unit=ID, TypeName="Temperature", Used=1, Description="ParameterID="+str(PID)+"\nDesignation="+str(Design)).Create()
        elif Unit == "A":
            if ID == 15:
                Domoticz.Device(Name=Name+" 1", Unit=ID, TypeName="Current (Single)", Used=1, Description="ParameterID="+str(PID)+"\nDesignation="+str(Design)).Create()
            if ID == 16:
                Domoticz.Device(Name=Name+" 2", Unit=ID, TypeName="Current (Single)", Used=1, Description="ParameterID="+str(PID)+"\nDesignation="+str(Design)).Create()
            if ID == 17:
                Domoticz.Device(Name=Name+" 3", Unit=ID, TypeName="Current (Single)", Used=1, Description="ParameterID="+str(PID)+"\nDesignation="+str(Design)).Create()
            if ID == 53:
                Domoticz.Device(Name=Name, Unit=ID, TypeName="Current (Single)", Used=1, Description="ParameterID="+str(PID)).Create()
        elif Name == "compressor starts":
            Domoticz.Device(Name=Name, Unit=ID, TypeName="Custom", Options={"Custom": "0;times"}, Used=1, Description="ParameterID="+str(PID)+"\nDesignation="+str(Design)).Create()
        elif Name == "blocked":
            if ID == 21:
                Domoticz.Device(Name="compressor "+Name, Unit=ID, TypeName="Text", Used=1, Description="ParameterID="+str(PID)).Create()
            if ID == 51:
                Domoticz.Device(Name="addition "+Name, Unit=ID, TypeName="Text", Used=1, Description="ParameterID="+str(PID)).Create()
        elif ID == 61 or ID == 71:
            Domoticz.Device(Name=Name, Unit=ID, TypeName="Text", Used=1, Description="ParameterID="+str(PID)).Create()
        elif ID == 41:
            Domoticz.Device(Name=Name, Unit=ID, TypeName="Text", Used=1, Description="ParameterID="+str(PID)+"\nDesignation="+str(Design)).Create()
        elif ID == 72 or ID == 73:
            Domoticz.Device(Name=Name, Unit=ID, TypeName="Text", Used=1).Create()
        elif ID == 74:
            Domoticz.Device(Name="software "+Name, Unit=ID, TypeName="Text", Used=1).Create()
        elif ID == 62:
            Domoticz.Device(Name="smart price adaption "+Name, Unit=ID, TypeName="Text", Used=1, Description="ParameterID="+str(PID)).Create()
        else:
            if Design == "":
                Domoticz.Device(Name=Name, Unit=ID, TypeName="Custom", Options={"Custom": "0;"+Unit}, Used=1, Description="ParameterID="+str(PID)).Create()
            else:
                Domoticz.Device(Name=Name, Unit=ID, TypeName="Custom", Options={"Custom": "0;"+Unit}, Used=1, Description="ParameterID="+str(PID)+"\nDesignation="+str(Design)).Create()

def CreateFile():
    if not os.path.isfile(_plugin.HomeDir+'/NIBEUplink.ini'):
        data = {}
        data["Config"] = []
        data["Config"].append({
             "Access": "",
             "Charge": "",
             "Ident": "",
             "Refresh": "",
             "Secret": "",
             "SystemID": "",
             "URL": ""
             })
        with open(_plugin.HomeDir+'/NIBEUplink.ini', 'w') as outfile:
            json.dump(data, outfile, indent=4)

def CheckFile(Parameter):
    if os.path.isfile(_plugin.HomeDir+'/NIBEUplink.ini'):
        with open(_plugin.HomeDir+'/NIBEUplink.ini') as jsonfile:
            data = json.load(jsonfile)
            data = data["Config"][0][Parameter]
            return data

def WriteFile(Parameter,text):
    CreateFile()
    with open(_plugin.HomeDir+'/NIBEUplink.ini') as jsonfile:
        data = json.load(jsonfile)
    data["Config"][0][Parameter] = text
    with open(_plugin.HomeDir+'/NIBEUplink.ini', 'w') as outfile:
        json.dump(data, outfile, indent=4)

def CheckInternet():
    WriteDebug("Entered CheckInternet")
    try:
        WriteDebug("Try ping")
        requests.get(url='https://api.nibeuplink.com/', timeout=15)
        WriteDebug("Ping done")
        return True
    except:
        if _plugin.GetCode.Connected():
            _plugin.GetCode.Disconnect()
        if _plugin.GetToken.Connected():
            _plugin.GetToken.Disconnect()
        if _plugin.GetData.Connected():
            _plugin.GetData.Disconnect()
        WriteDebug("Internet is not available")
        return False

def WriteDebug(text):
    if Parameters["Mode6"] == "Yes":
        timenow = (datetime.now())
        file = open(_plugin.HomeDir+"/NIBEUplink.log","a")
        file.write(str(timenow)+" "+text+"\n")
        file.close()

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)

def onMessage(Connection, Data):
    _plugin.onMessage(Connection, Data)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

    # Generic helper functions
def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug( "'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
    return
