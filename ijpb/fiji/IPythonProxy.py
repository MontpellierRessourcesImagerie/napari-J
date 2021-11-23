import subprocess
import sys
from ij import IJ
from threading import Thread
import time

class IPythonProxy:

	def __init__(self):
		self.connectionFile = IJ.getProperty('jupter_connection_file')		
		self.pythonExecutable = IJ.getProperty('python_executable')		
		self.out = ''
		self.connect()
		self.createKernelClient()

	def deal_with_stdout(self):
		while(not self.stopped):
			for line in self.python.stdout:
				print(line)
				self.out = self.out + line 
				self.cont = True

	def createKernelClient(self):
		self.pythonRun("from jupyter_client.blocking import BlockingKernelClient")
		self.pythonRun("kc = BlockingKernelClient(connection_file='"+self.connectionFile+"')")
		self.pythonRun("kc.load_connection_file()")
		self.pythonRun("kc.start_channels()")
		
	def connect(self):
		self.history = []
		self.python = subprocess.Popen([self.pythonExecutable + ' -i -u'],
		                       shell=True,
		                       stdin=subprocess.PIPE,
		                       stdout=subprocess.PIPE,
		                       stderr=subprocess.PIPE)
		self.thread = Thread(target=self.deal_with_stdout, args=[])
		self.thread.setDaemon(True)
		self.stopped = False
		self.thread.start()       

	def pythonRun(self, command, wait=False):
		self.cont = False
		self.python.stdin.write(command + "\n")
		self.python.stdin.flush()   	
		print(command)
		if not wait:
			return
		while not self.cont:
			time.sleep(0.02)

	def run(self, command, wait=False):
		self.pythonRun("msgid = kc.execute_interactive('"+command+"')\n")
		self.out = self.out + (">>>" + command + "\n")
		if wait:
			self.pythonRun("res = kc.get_shell_msg(msgid, timeout=0)")		
			self.pythonRun('print(res)', wait=True)

	def disconnect(self):
		self.pythonRun("exit()")
		time.sleep(2)   
		result = self.python.communicate()
		IJ.log(self.out)
		self.stopped = True
		self.thread.join()
		self.python.terminate()

