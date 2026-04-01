#!/usr/bin/env python3
"""
WiFi Security Scanner - Windows Version
Now with Rogue Type Detection and Confidence Scoring
"""

import subprocess
import platform
import re
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from datetime import datetime
from collections import defaultdict
import time


class WiFiSecurityScanner:
    """Scans all WiFi networks on Windows"""

    def __init__(self):
        self.currentOS = platform.system()
        self.foundNetworks = []

        if self.currentOS != "Windows":
            raise Exception("This program only works on Windows. Current OS: " + self.currentOS)

    def scanNetworks(self):
        """Scan for all WiFi networks on Windows"""
        return self.scanAllWindowsNetworks()

    def scanAllWindowsNetworks(self):
        """Enhanced Windows scanning to get all available networks"""
        networks = []
        networkDataMap = {}

        try:
            print("Refreshing network list...")
            subprocess.run(
                ['netsh', 'wlan', 'disconnect'],
                capture_output=True,
                shell=True,
                timeout=2
            )
            time.sleep(1)

            # trigger a fresh scan on all available interfaces
            try:
                interfaceResult = subprocess.run(
                    ['netsh', 'wlan', 'show', 'interfaces'],
                    capture_output=True,
                    text=True,
                    shell=True
                )

                interfaceNames = []
                for line in interfaceResult.stdout.split('\n'):
                    if 'Name' in line and ':' in line:
                        name = line.split(':')[1].strip()
                        if name:
                            interfaceNames.append(name)

                for interfaceName in interfaceNames:
                    try:
                        subprocess.run(
                            ['netsh', 'wlan', 'scan', f'interface={interfaceName}'],
                            capture_output=True,
                            shell=True,
                            timeout=3
                        )
                    except:
                        pass

                time.sleep(2)

            except Exception as e:
                print(f"Scan trigger warning: {e}")

            print("Getting all available networks...")
            scanResult = subprocess.run(
                ['netsh', 'wlan', 'show', 'networks', 'mode=Bssid'],
                capture_output=True,
                text=True,
                shell=True
            )

            rawOutput = scanResult.stdout

            # check saved profiles so we can flag networks the user has connected to before
            savedProfilesResult = subprocess.run(
                ['netsh', 'wlan', 'show', 'profiles'],
                capture_output=True,
                text=True,
                shell=True
            )

            savedNetworkNames = set()
            for line in savedProfilesResult.stdout.split('\n'):
                if 'All User Profile' in line and ':' in line:
                    profileName = line.split(':')[1].strip()
                    savedNetworkNames.add(profileName)

            currentNetwork = {}
            currentBSSID = {}

            for line in rawOutput.split('\n'):
                line = line.strip()

                if line.startswith("SSID"):
                    ssidMatch = re.match(r'SSID\s+\d+\s*:\s*(.+)', line)
                    if ssidMatch:
                        ssid = ssidMatch.group(1).strip()

                        if currentNetwork and 'ssid' in currentNetwork:
                            if currentNetwork['ssid'] not in networkDataMap:
                                networkDataMap[currentNetwork['ssid']] = currentNetwork

                        currentNetwork = {
                            'ssid': ssid,
                            'bssids': [],
                            'saved': ssid in savedNetworkNames,
                            'visible': True
                        }

                elif "Network type" in line and ':' in line:
                    currentNetwork['type'] = line.split(':')[1].strip()

                elif "Authentication" in line and ':' in line:
                    currentNetwork['authentication'] = line.split(':')[1].strip()

                elif "Encryption" in line and ':' in line:
                    currentNetwork['encryption'] = line.split(':')[1].strip()

                elif line.startswith("BSSID"):
                    bssidMatch = re.match(r'BSSID\s+\d+\s*:\s*([a-fA-F0-9:]+)', line)
                    if bssidMatch:
                        currentBSSID = {'bssid': bssidMatch.group(1).upper()}
                        if 'bssids' in currentNetwork:
                            currentNetwork['bssids'].append(currentBSSID)

                elif "Signal" in line and ':' in line and currentBSSID:
                    signalMatch = re.search(r'(\d+)%', line)
                    if signalMatch:
                        signalStrength = int(signalMatch.group(1))
                        currentBSSID['signal'] = signalStrength
                        currentBSSID['signal_dbm'] = (signalStrength / 2) - 100

                elif "Radio type" in line and ':' in line and currentBSSID:
                    currentBSSID['radio'] = line.split(':')[1].strip()

                elif "Channel" in line and ':' in line and currentBSSID:
                    channelMatch = re.search(r'(\d+)', line)
                    if channelMatch:
                        currentBSSID['channel'] = int(channelMatch.group(1))

                elif "Band" in line and ':' in line and currentBSSID:
                    currentBSSID['band'] = line.split(':')[1].strip()

            if currentNetwork and 'ssid' in currentNetwork:
                if currentNetwork['ssid'] not in networkDataMap:
                    networkDataMap[currentNetwork['ssid']] = currentNetwork

            networks = list(networkDataMap.values())
            networks = [n for n in networks if n.get('ssid') and (n['ssid'] != '' or n.get('type') == 'Hidden')]

            print(f"Found {len(networks)} networks")

        except Exception as e:
            print(f"Error during scanning: {e}")
            networks = self.simpleScan()

        return networks

    def simpleScan(self):
        """Fallback scanning method if the main scan fails"""
        networks = []
        try:
            result = subprocess.run(
                ['netsh', 'wlan', 'show', 'networks'],
                capture_output=True,
                text=True,
                shell=True
            )

            currentNetwork = {}
            for line in result.stdout.split('\n'):
                if 'SSID' in line and ':' in line:
                    ssid = line.split(':')[1].strip()
                    if ssid:
                        if currentNetwork:
                            networks.append(currentNetwork)
                        currentNetwork = {
                            'ssid': ssid,
                            'bssids': [{'bssid': 'N/A', 'signal': 50}],
                            'authentication': 'Unknown',
                            'encryption': 'Unknown'
                        }
                elif 'Authentication' in line and ':' in line:
                    currentNetwork['authentication'] = line.split(':')[1].strip()
                elif 'Encryption' in line and ':' in line:
                    currentNetwork['encryption'] = line.split(':')[1].strip()

            if currentNetwork:
                networks.append(currentNetwork)

        except Exception as e:
            print(f"Simple scan error: {e}")

        return networks


class RogueTypeDetector:
    """Detects and classifies types of rogue WiFi networks"""

    def __init__(self):
        self.rogueTypeDefinitions = {
            'Evil Twin': {
                'indicators': ['duplicate_ssid', 'different_mac', 'stronger_signal'],
                'weight': 1.0
            },
            'Honeypot': {
                'indicators': ['open_network', 'suspicious_name', 'strong_signal'],
                'weight': 0.9
            },
            'Karma Attack': {
                'indicators': ['multiple_ssids', 'same_mac', 'probe_responses'],
                'weight': 0.8
            },
            'Pineapple': {
                'indicators': ['default_ssid', 'open_network', 'strong_signal'],
                'weight': 0.85
            },
            'Ad-hoc Rogue': {
                'indicators': ['ad_hoc_mode', 'peer_to_peer', 'no_encryption'],
                'weight': 0.7
            },
            'Soft AP': {
                'indicators': ['mobile_hotspot_pattern', 'random_mac', 'varying_signal'],
                'weight': 0.6
            },
            'MAC Spoofing': {
                'indicators': ['fake_mac', 'vendor_mismatch', 'impossible_mac'],
                'weight': 0.75
            }
        }

    def detectRogueType(self, networkAnalysis):
        """
        Detect the type of rogue network with confidence percentage.
        Returns a tuple of (type, confidence_percentage)
        """
        if networkAnalysis['safety_score'] >= 70:
            return "No rogue WiFi", 100

        collectedEvidence = self.collectEvidence(networkAnalysis)
        rogueScores = {}

        for rogueType, characteristics in self.rogueTypeDefinitions.items():
            score = self.calculateTypeScore(collectedEvidence, characteristics)
            if score > 0:
                rogueScores[rogueType] = score

        if not rogueScores:
            if networkAnalysis['safety_score'] < 30:
                return "Unknown Rogue", 100 - networkAnalysis['safety_score']
            else:
                return "Suspicious Network", 100 - networkAnalysis['safety_score']

        mostLikelyType = max(rogueScores, key=rogueScores.get)
        confidence = min(int(rogueScores[mostLikelyType]), 95)

        return f"{mostLikelyType}", confidence

    def collectEvidence(self, analysis):
        """Collect all suspicious signals from the network analysis"""
        evidence = set()
        features = analysis.get('features', {})

        if not features.get('Duplicate SSID', {}).get('safe', True):
            evidence.add('duplicate_ssid')
            evidence.add('different_mac')

            if 'SUSPICIOUSLY STRONG' in features.get('Signal Anomaly', {}).get('reason', ''):
                evidence.add('stronger_signal')

        if not features.get('Signal Anomaly', {}).get('safe', True):
            signalReason = features.get('Signal Anomaly', {}).get('reason', '')
            if 'SUSPICIOUSLY STRONG' in signalReason or 'Very strong' in signalReason:
                evidence.add('strong_signal')
                evidence.add('stronger_signal')

        if not features.get('Encryption', {}).get('safe', True):
            encryptionReason = features.get('Encryption', {}).get('reason', '')
            if 'NO PASSWORD' in encryptionReason or 'Open' in encryptionReason:
                evidence.add('open_network')
                evidence.add('no_encryption')
            elif 'WEP' in encryptionReason:
                evidence.add('weak_encryption')

        if not features.get('MAC Pattern', {}).get('safe', True):
            macReason = features.get('MAC Pattern', {}).get('reason', '')
            if 'FAKE MAC' in macReason:
                evidence.add('fake_mac')
                evidence.add('impossible_mac')
            elif 'Randomized' in macReason:
                evidence.add('random_mac')

        networkName = analysis.get('name', '')
        if any(word in networkName.lower() for word in ['free', 'public', 'open', 'guest']):
            evidence.add('suspicious_name')

        if any(word in networkName.lower() for word in ['linksys', 'netgear', 'default', 'dlink']):
            evidence.add('default_ssid')

        if any(word in networkName.lower() for word in ['iphone', 'android', 'mobile', 'hotspot']):
            evidence.add('mobile_hotspot_pattern')

        if analysis.get('network_type') == 'Ad-hoc':
            evidence.add('ad_hoc_mode')
            evidence.add('peer_to_peer')

        return evidence

    def calculateTypeScore(self, evidence, characteristics):
        """Score a rogue type based on how many of its indicators are present"""
        indicators = characteristics['indicators']
        weight = characteristics['weight']

        matchCount = sum(1 for indicator in indicators if indicator in evidence)

        if matchCount == 0:
            return 0

        matchPercentage = (matchCount / len(indicators)) * 100
        finalScore = matchPercentage * weight

        if matchCount >= 2:
            finalScore *= 1.2

        return min(finalScore, 95)


class SecurityAnalyzer:
    """Analyzes WiFi networks for security issues and rogue network types"""

    def __init__(self):
        self.featuresToCheck = [
            "Duplicate SSID",
            "Signal Anomaly",
            "Encryption",
            "MAC Pattern"
        ]
        self.rogueDetector = RogueTypeDetector()

    def analyzeNetworks(self, networks):
        """Analyze each network and attach a rogue type classification"""
        analyzedNetworks = []

        # group by SSID so we can spot duplicate network names
        networksBySSID = defaultdict(list)
        for net in networks:
            ssid = net.get('ssid', '')
            if ssid:
                networksBySSID[ssid].append(net)

        for network in networks:
            analysis = self.analyzeSingleNetwork(network, networksBySSID)

            rogueType, confidence = self.rogueDetector.detectRogueType(analysis)
            analysis['rogue_type'] = rogueType
            analysis['rogue_confidence'] = confidence

            analyzedNetworks.append(analysis)

        return analyzedNetworks

    def analyzeSingleNetwork(self, network, networksBySSID):
        """Run all security checks on a single network"""
        ssid = network.get('ssid', 'Hidden')

        analysis = {
            'name': ssid,
            'safety_score': 100,
            'connected': network.get('connected', False),
            'saved': network.get('saved', False),
            'network_type': network.get('type', 'Infrastructure'),
            'features': {
                'Duplicate SSID': {'safe': True, 'reason': 'No suspicious activity'},
                'Signal Anomaly': {'safe': True, 'reason': 'No suspicious activity'},
                'Encryption':     {'safe': True, 'reason': 'No suspicious activity'},
                'MAC Pattern':    {'safe': True, 'reason': 'No suspicious activity'}
            }
        }

        # check if multiple routers are broadcasting the same name (evil twin indicator)
        if ssid in networksBySSID and len(networksBySSID[ssid]) > 1:
            uniqueMACs = set()
            for net in networksBySSID[ssid]:
                for bssidInfo in net.get('bssids', []):
                    mac = bssidInfo.get('bssid')
                    if mac and mac != 'Unknown' and mac != 'N/A':
                        uniqueMACs.add(mac)

            if len(uniqueMACs) > 1:
                analysis['safety_score'] -= 40
                analysis['features']['Duplicate SSID'] = {
                    'safe': False,
                    'reason': f'EVIL TWIN: {len(uniqueMACs)} routers with same name detected!'
                }

        # check if signal is unusually strong, which could mean a rogue AP is very close
        for bssidInfo in network.get('bssids', []):
            signalStrength = bssidInfo.get('signal', 0)
            signalDBM = bssidInfo.get('signal_dbm', -70)

            if signalStrength > 95 or signalDBM > -35:
                analysis['safety_score'] -= 30
                analysis['features']['Signal Anomaly'] = {
                    'safe': False,
                    'reason': f'SUSPICIOUSLY STRONG: {signalStrength}% - Possible rogue AP very close by'
                }
            elif signalStrength > 90:
                analysis['safety_score'] -= 15
                analysis['features']['Signal Anomaly'] = {
                    'safe': False,
                    'reason': f'Very strong signal ({signalStrength}%)'
                }

        # check encryption type
        encryptionType = network.get('encryption', 'Unknown')
        authType = network.get('authentication', 'Unknown')

        if encryptionType == 'Open' or authType == 'Open' or 'Open' in str(authType):
            analysis['safety_score'] -= 50
            analysis['features']['Encryption'] = {
                'safe': False,
                'reason': 'NO PASSWORD - Anyone can connect and intercept data!'
            }
        elif 'WEP' in str(encryptionType) or 'WEP' in str(authType):
            analysis['safety_score'] -= 40
            analysis['features']['Encryption'] = {
                'safe': False,
                'reason': 'WEAK WEP encryption - Easily crackable!'
            }
        elif 'WPA3' in str(authType):
            analysis['features']['Encryption']['reason'] = 'Strong WPA3 encryption'
        elif 'WPA2' in str(authType):
            analysis['features']['Encryption']['reason'] = 'Good WPA2 encryption'

        # check MAC address for spoofing patterns
        for bssidInfo in network.get('bssids', []):
            macAddress = bssidInfo.get('bssid', '')

            if macAddress and macAddress not in ['Unknown', 'N/A']:
                knownFakeMACs = ['00:00:00', 'FF:FF:FF', 'DE:AD:BE', '12:34:56', '11:22:33']

                for fakeMAC in knownFakeMACs:
                    if macAddress.upper().startswith(fakeMAC):
                        analysis['safety_score'] -= 35
                        analysis['features']['MAC Pattern'] = {
                            'safe': False,
                            'reason': f'FAKE MAC: {macAddress} - Spoofed address!'
                        }
                        break

                # check if the device is using a randomized MAC to hide its identity
                if analysis['features']['MAC Pattern']['safe']:
                    try:
                        firstOctet = int(macAddress.split(':')[0], 16)
                        if firstOctet & 0x02:
                            analysis['safety_score'] -= 10
                            analysis['features']['MAC Pattern'] = {
                                'safe': False,
                                'reason': f'Randomized MAC: {macAddress[:8]}... - Device hiding identity'
                            }
                    except:
                        pass

        analysis['safety_score'] = max(0, min(100, analysis['safety_score']))

        return analysis


class WiFiSecurityGUI:
    """Main GUI window showing all networks with security analysis and rogue type detection"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("WiFi Security Scanner - Rogue Type Detection")
        self.root.geometry("1600x800")

        if platform.system() != "Windows":
            messagebox.showerror("OS Error", "This program only works on Windows!")
            self.root.destroy()
            return

        self.scanner = WiFiSecurityScanner()
        self.analyzer = SecurityAnalyzer()

        self.buildGUI()

    def buildGUI(self):
        """Build the main window with the network table and controls"""
        headerFrame = tk.Frame(self.root, bg='#2c3e50', height=80)
        headerFrame.pack(fill=tk.X)
        headerFrame.pack_propagate(False)

        tk.Label(
            headerFrame,
            text="WiFi Security Scanner with Rogue Type Detection",
            font=('Arial', 20, 'bold'),
            fg='white',
            bg='#2c3e50'
        ).pack(pady=(15, 5))

        tk.Label(
            headerFrame,
            text="Identifies specific types of rogue networks with confidence levels",
            font=('Arial', 10),
            fg='#ecf0f1',
            bg='#2c3e50'
        ).pack()

        buttonFrame = tk.Frame(self.root)
        buttonFrame.pack(pady=10)

        self.scanButton = tk.Button(
            buttonFrame,
            text="Scan ALL Networks",
            command=self.startScan,
            font=('Arial', 12, 'bold'),
            bg='#3498db',
            fg='white',
            padx=20,
            pady=10
        )
        self.scanButton.pack(side=tk.LEFT, padx=5)

        self.statusLabel = tk.Label(
            buttonFrame,
            text="Ready to scan and detect rogue types",
            font=('Arial', 10)
        )
        self.statusLabel.pack(side=tk.LEFT, padx=20)

        tk.Label(
            buttonFrame,
            text="Run as Admin for best results",
            font=('Arial', 9),
            fg='orange'
        ).pack(side=tk.LEFT, padx=10)

        tableFrame = tk.Frame(self.root)
        tableFrame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        columnNames = ['Network Name', 'Safe/Unsafe', 'Rogue Type', 'Duplicate SSID',
                       'Signal Anomaly', 'Encryption', 'MAC Pattern']

        self.networkTable = ttk.Treeview(tableFrame, columns=columnNames, show='headings', height=20)

        self.networkTable.heading('Network Name',   text='Network Name')
        self.networkTable.heading('Safe/Unsafe',    text='Safe/Unsafe')
        self.networkTable.heading('Rogue Type',     text='Rogue Type (Confidence)')
        self.networkTable.heading('Duplicate SSID', text='Duplicate SSID')
        self.networkTable.heading('Signal Anomaly', text='Signal Anomaly')
        self.networkTable.heading('Encryption',     text='Encryption')
        self.networkTable.heading('MAC Pattern',    text='MAC Pattern')

        self.networkTable.column('Network Name',   width=180)
        self.networkTable.column('Safe/Unsafe',    width=100)
        self.networkTable.column('Rogue Type',     width=180)
        self.networkTable.column('Duplicate SSID', width=220)
        self.networkTable.column('Signal Anomaly', width=220)
        self.networkTable.column('Encryption',     width=220)
        self.networkTable.column('MAC Pattern',    width=220)

        tableScrollbar = ttk.Scrollbar(tableFrame, orient='vertical', command=self.networkTable.yview)
        self.networkTable.configure(yscrollcommand=tableScrollbar.set)

        self.networkTable.pack(side='left', fill='both', expand=True)
        tableScrollbar.pack(side='right', fill='y')

        self.buildLegend()

        self.networkTable.bind('<Double-Button-1>', self.showNetworkDetails)

    def buildLegend(self):
        """Build the legend section at the bottom of the window"""
        legendFrame = tk.Frame(self.root, bg='#ecf0f1')
        legendFrame.pack(fill=tk.X, padx=20, pady=10)

        safetyFrame = tk.Frame(legendFrame, bg='#ecf0f1')
        safetyFrame.pack(side=tk.LEFT, padx=20)

        tk.Label(
            safetyFrame,
            text="Safety Levels:",
            font=('Arial', 10, 'bold'),
            bg='#ecf0f1'
        ).pack(anchor='w')

        tk.Label(safetyFrame, text="[GREEN]  SAFE (70-100%)",   font=('Arial', 9), fg='green',  bg='#ecf0f1').pack(anchor='w')
        tk.Label(safetyFrame, text="[YELLOW] CAUTION (30-70%)", font=('Arial', 9), fg='orange', bg='#ecf0f1').pack(anchor='w')
        tk.Label(safetyFrame, text="[RED]    UNSAFE (0-30%)",   font=('Arial', 9), fg='red',    bg='#ecf0f1').pack(anchor='w')

        rogueTypesFrame = tk.Frame(legendFrame, bg='#ecf0f1')
        rogueTypesFrame.pack(side=tk.LEFT, padx=20)

        tk.Label(
            rogueTypesFrame,
            text="Rogue Types:",
            font=('Arial', 10, 'bold'),
            bg='#ecf0f1'
        ).pack(anchor='w')

        rogueTypeDescriptions = [
            ("Evil Twin",    "Fake copy of legitimate network"),
            ("Honeypot",     "Trap network to steal data"),
            ("Pineapple",    "Professional hacking device"),
            ("Karma Attack", "Responds to all connection requests")
        ]

        for rogueType, description in rogueTypeDescriptions:
            tk.Label(
                rogueTypesFrame,
                text=f"  {rogueType}: {description}",
                font=('Arial', 8),
                bg='#ecf0f1'
            ).pack(anchor='w')

        instructionsFrame = tk.Frame(legendFrame, bg='#ecf0f1')
        instructionsFrame.pack(side=tk.LEFT, padx=20)

        tk.Label(
            instructionsFrame,
            text="Instructions:",
            font=('Arial', 10, 'bold'),
            bg='#ecf0f1'
        ).pack(anchor='w')

        tk.Label(instructionsFrame, text="  Double-click any network for details",   font=('Arial', 9), bg='#ecf0f1').pack(anchor='w')
        tk.Label(instructionsFrame, text="  Percentage shows detection confidence",  font=('Arial', 9), bg='#ecf0f1').pack(anchor='w')
        tk.Label(instructionsFrame, text="  [saved] = Previously saved network",     font=('Arial', 9), bg='#ecf0f1').pack(anchor='w')

    def startScan(self):
        """Kick off a network scan and clear the previous results"""
        self.scanButton.config(state='disabled', text='Scanning...')
        self.statusLabel.config(text='Scanning all networks and detecting rogue types...')

        for item in self.networkTable.get_children():
            self.networkTable.delete(item)

        self.networkTable.insert('', 'end', values=(
            'Scanning...',
            'Please wait',
            'Analyzing...',
            'Refreshing list...',
            'Takes 5-10 seconds',
            'Getting networks',
            'Please wait...'
        ))

        scanThread = threading.Thread(target=self.runScanInBackground)
        scanThread.start()

    def runScanInBackground(self):
        """Run the actual scan off the main thread so the UI stays responsive"""
        foundNetworks = self.scanner.scanNetworks()

        self.root.after(0, lambda: [self.networkTable.delete(item) for item in self.networkTable.get_children()])

        if not foundNetworks:
            self.root.after(0, self.showNoNetworksMessage)
            return

        analyzedNetworks = self.analyzer.analyzeNetworks(foundNetworks)
        analyzedNetworks.sort(key=lambda x: -x['safety_score'])

        self.root.after(0, self.populateTable, analyzedNetworks)

    def populateTable(self, analyzedNetworks):
        """Fill the table with the scan results"""
        for analysis in analyzedNetworks:
            safetyScore = analysis['safety_score']
            if safetyScore >= 70:
                safetyLabel = f"SAFE {safetyScore}%"
                rowTag = 'safe'
            elif safetyScore >= 30:
                safetyLabel = f"CAUTION {safetyScore}%"
                rowTag = 'caution'
            else:
                safetyLabel = f"UNSAFE {safetyScore}%"
                rowTag = 'unsafe'

            displayName = analysis['name']
            if analysis.get('saved'):
                displayName += " [saved]"

            rogueType       = analysis.get('rogue_type', 'Unknown')
            rogueConfidence = analysis.get('rogue_confidence', 0)

            if rogueType == "No rogue WiFi":
                rogueDisplay = "[SAFE] No rogue WiFi"
                rogueTag = 'safe_rogue'
            else:
                if rogueConfidence >= 80:
                    confidenceLabel = "[HIGH]"
                elif rogueConfidence >= 60:
                    confidenceLabel = "[WARN]"
                else:
                    confidenceLabel = "[?]"

                rogueDisplay = f"{confidenceLabel} {rogueType} ({rogueConfidence}%)"

                if rogueConfidence >= 80:
                    rogueTag = 'high_confidence'
                elif rogueConfidence >= 60:
                    rogueTag = 'medium_confidence'
                else:
                    rogueTag = 'low_confidence'

            features = analysis['features']
            featureTexts = []
            for featureName in ['Duplicate SSID', 'Signal Anomaly', 'Encryption', 'MAC Pattern']:
                featureInfo = features.get(featureName, {})
                if featureInfo.get('safe'):
                    featureTexts.append('No suspicious activity')
                else:
                    featureTexts.append(featureInfo.get('reason', 'Issue detected'))

            self.networkTable.insert('', 'end', values=(
                displayName,
                safetyLabel,
                rogueDisplay,
                featureTexts[0],
                featureTexts[1],
                featureTexts[2],
                featureTexts[3]
            ), tags=(rowTag, rogueTag))

        self.networkTable.tag_configure('safe',            foreground='green')
        self.networkTable.tag_configure('caution',         foreground='orange')
        self.networkTable.tag_configure('unsafe',          foreground='red')
        self.networkTable.tag_configure('safe_rogue',      foreground='green')
        self.networkTable.tag_configure('high_confidence', foreground='darkred')
        self.networkTable.tag_configure('medium_confidence', foreground='darkorange')
        self.networkTable.tag_configure('low_confidence',  foreground='brown')

        self.scanButton.config(state='normal', text='Scan ALL Networks')
        self.statusLabel.config(text=f'Found {len(analyzedNetworks)} networks - Rogue types identified')

    def showNoNetworksMessage(self):
        """Show a helpful message when no networks were found"""
        self.networkTable.insert('', 'end', values=(
            'No networks found',
            'Check:',
            'N/A',
            '1. WiFi is enabled',
            '2. Run as Administrator',
            '3. WiFi adapter working',
            '4. Try again'
        ))

        self.scanButton.config(state='normal', text='Scan ALL Networks')
        self.statusLabel.config(text='No networks found - check WiFi is enabled')

    def showNetworkDetails(self, event):
        """Open a popup with full details about the selected network"""
        selection = self.networkTable.selection()
        if not selection:
            return

        selectedItem = selection[0]
        rowValues    = self.networkTable.item(selectedItem, 'values')

        if rowValues[0] == 'No networks found':
            return

        detailsPopup = tk.Toplevel(self.root)
        detailsPopup.title(f"Network Details: {rowValues[0]}")
        detailsPopup.geometry("700x600")

        popupHeader = tk.Frame(detailsPopup, bg='#2c3e50', height=60)
        popupHeader.pack(fill=tk.X)
        popupHeader.pack_propagate(False)

        tk.Label(
            popupHeader,
            text=f"Network: {rowValues[0]}",
            font=('Arial', 16, 'bold'),
            fg='white',
            bg='#2c3e50'
        ).pack(pady=15)

        contentFrame = tk.Frame(detailsPopup, padx=20, pady=20)
        contentFrame.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            contentFrame,
            text=f"Safety Status: {rowValues[1]}",
            font=('Arial', 12, 'bold')
        ).pack(anchor='w', pady=(0, 10))

        rogueSection = tk.LabelFrame(contentFrame, text="Rogue Network Detection", font=('Arial', 11, 'bold'))
        rogueSection.pack(fill=tk.X, pady=(0, 15))

        tk.Label(
            rogueSection,
            text=f"Type: {rowValues[2]}",
            font=('Arial', 10)
        ).pack(anchor='w', padx=10, pady=5)

        detectedType = rowValues[2].split('(')[0].strip()

        rogueExplanations = {
            "[HIGH] Evil Twin":    "This appears to be a fake copy of a legitimate network. "
                                   "Attackers create these to trick you into connecting to their network instead of the real one.",
            "[HIGH] Honeypot":     "This network is designed to attract victims. "
                                   "It offers free/open access to steal your data once connected.",
            "[HIGH] Pineapple":    "This may be a WiFi Pineapple - a professional hacking device "
                                   "that can intercept all your internet traffic.",
            "[WARN] Karma Attack": "This network responds to any connection request, "
                                   "pretending to be whatever network your device is looking for.",
            "[SAFE] No rogue WiFi":"This network shows no signs of being a rogue access point. "
                                   "It appears to be legitimate based on our analysis."
        }

        for typeKey, explanation in rogueExplanations.items():
            if typeKey in rowValues[2] or detectedType in typeKey:
                tk.Label(
                    rogueSection,
                    text=explanation,
                    font=('Arial', 9),
                    wraplength=600,
                    justify='left'
                ).pack(anchor='w', padx=10, pady=5)
                break

        securitySection = tk.LabelFrame(contentFrame, text="Security Analysis", font=('Arial', 11, 'bold'))
        securitySection.pack(fill=tk.BOTH, expand=True)

        securityText = tk.Text(securitySection, wrap=tk.WORD, height=10)
        securityText.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        featureLabels = ['Duplicate SSID', 'Signal Anomaly', 'Encryption', 'MAC Pattern']
        for i, featureLabel in enumerate(featureLabels, 3):
            securityText.insert(tk.END, f"{featureLabel}:\n", 'bold')
            securityText.insert(tk.END, f"  {rowValues[i]}\n\n")

        securityText.config(state='disabled')
        securityText.tag_configure('bold', font=('Arial', 10, 'bold'))

        recommendationsSection = tk.LabelFrame(contentFrame, text="Recommendations", font=('Arial', 11, 'bold'))
        recommendationsSection.pack(fill=tk.X, pady=(15, 0))

        if "No rogue" in rowValues[2]:
            recommendations = [
                "[OK]  This network appears safe to use",
                "[OK]  Normal browsing and activities should be fine",
                "[TIP] Still use VPN for sensitive activities"
            ]
            recommendationColor = 'green'
        elif any(x in rowValues[2] for x in ['Evil Twin', 'Honeypot', 'Pineapple']):
            recommendations = [
                "[!] DO NOT connect to this network!",
                "[!] High risk of data theft and surveillance",
                "[!] Find an alternative secure network",
                "[!] Use cellular data instead if possible"
            ]
            recommendationColor = 'red'
        else:
            recommendations = [
                "[WARN] Be cautious with this network",
                "[WARN] Avoid banking or shopping",
                "[WARN] Use VPN if you must connect",
                "[WARN] Consider using cellular data instead"
            ]
            recommendationColor = 'orange'

        for recommendation in recommendations:
            tk.Label(
                recommendationsSection,
                text=recommendation,
                font=('Arial', 9),
                fg=recommendationColor
            ).pack(anchor='w', padx=10, pady=2)

        tk.Button(
            detailsPopup,
            text="Close",
            command=detailsPopup.destroy,
            font=('Arial', 10),
            bg='#3498db',
            fg='white',
            padx=20,
            pady=5
        ).pack(pady=15)

    def run(self):
        """Start the application"""
        self.root.mainloop()


def main():
    """Entry point for the WiFi scanner"""

    if platform.system() != "Windows":
        print("=" * 80)
        print("ERROR: This program only works on Windows!")
        print(f"Your current OS: {platform.system()}")
        print("=" * 80)
        input("Press Enter to exit...")
        return

    print("=" * 80)
    print("WiFi Security Scanner with Rogue Type Detection")
    print("Identifies specific types of rogue networks")
    print("=" * 80)
    print("\nIMPORTANT:")
    print("  For best results (to see all networks):")
    print("  1. Right-click and 'Run as Administrator'")
    print("  2. Make sure WiFi is turned ON")
    print("  3. Wait 5-10 seconds for full scan")
    print("\nRogue types detected:")
    print("  - Evil Twin    : Fake copies of legitimate networks")
    print("  - Honeypot     : Trap networks to steal data")
    print("  - Pineapple    : Professional hacking devices")
    print("  - Karma Attack : Responds to all requests")
    print("\nStarting scanner...\n")

    try:
        app = WiFiSecurityGUI()
        app.run()
    except Exception as e:
        print(f"\nError: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure WiFi is enabled")
        print("2. Try running as Administrator")
        print("3. Check if 'netsh' command works in Command Prompt")
        input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()
