'''

Setting Driver and Driven Knobs

'''




#------------------------------------------------------------------------------
#-Module Import
#------------------------------------------------------------------------------




import nuke, nukescripts 
from Qt import QtWidgets, QtGui, QtCore
import platform
import os
import re
import logging



#------------------------------------------------------------------------------
#-Header
#------------------------------------------------------------------------------




__VERSION__		= '1.2'
__OS__			= platform.system()
__AUTHOR__		= "Tianlun Jiang"
__WEBSITE__		= "jiangovfx.com"
__COPYRIGHT__	= "copyright (c) %s - %s" % (__AUTHOR__, __WEBSITE__)

__TITLE__		= "KnobDriver v%s" % __VERSION__


def _version_():
	ver='''

	version 1.2
	- fixing knob EQ key error
	- add sync function

	version 1.1
	- fixing driver knob numbering increasing issue
	- add invert button

	version 1.0
    - beta version
	- Create driver controls and stores driven knobs in Tooltip in '-nodename.knob' format
	- Driver controls includes:
		- SLIDER (Double_Knob)
		- RGBA (AColor_Knob)
		- XY (XY_Knob)
		- XYZ (XYZ_Knob)
		- INT (Int_Knob)
	- Only matching knob types will be linked
	- Button to refresh or sync Driven List in each Driver Knob

	'''
	return ver




#-------------------------------------------------------------------------------
#-Global Variables
#-------------------------------------------------------------------------------




STR_PLUS = '<b style="color: lightgreen">+</b> {}'
STR_SETDRIVEN = '<b>-&lt;-'
STR_LISTDRIVEN = '<b>&#8801;'
STR_SYNC = '<p>&#8634;'
STR_CMD_SETUP = "reload(mod_KnobDriver)\nmod_KnobDriver.{}" 
DIR_TYPES = {
	'SLIDER': 'Double_Knob',
	'RGBA': 'AColor_Knob',
	'XY': 'XY_Knob',
	'XYZ': 'XYZ_Knob',
	'INT': 'Int_Knob',
	'BOOL': 'Boolean_Knob'
}

RE_D = re.compile('\d+')
CLASS_EQ = {
	'Double_Knob': ['Double_Knob', 'Array_Knob', 'AColor_Knob', 'WH_Knob', 'Scale_Knob'],
	'Array_Knob': ['Double_Knob', 'Array_Knob', 'AColor_Knob', 'WH_Knob', 'Scale_Knob'],
	'AColor_Knob': ['AColor_Knob'],
	'XY_Knob': ['XY_Knob'],
	'XYZ_Knob': ['XYZ_Knob'],
	'Int_Knob': ['Int_Knob'],
	'Boolean_Knob': ['Boolean_Knob']
}




#-------------------------------------------------------------------------------
#-Main Function
#-------------------------------------------------------------------------------




def get_master_driver():
	"""Get Master Driver Node, create one if not in DAG
	return: (obj) Master Driver Node
	"""

	node = nuke.toNode('MASTER_DRIVER')

	if not node:
		node = nuke.nodes.NoOp(name='MASTER_DRIVER')
		# Tab
		k_id = nuke.Tab_Knob('tb_id', 'MASTER_DRIVER')
		node.addKnob(k_id)
		# Driver Buttons
		build_driver_types('SLIDER', node, newline=True)
		build_driver_types('RGBA', node)
		build_driver_types('XY', node)
		build_driver_types('XYZ', node)
		build_driver_types('INT', node)
		build_driver_types('BOOL', node)
		k_sync = nuke.PyScript_Knob('sync', STR_SYNC)
		k_sync.clearFlag(nuke.STARTLINE)
		k_sync.setCommand(STR_CMD_SETUP.format('sync_list_driven()'))
		node.addKnob(k_sync)
		# Divider
		node.addKnob(nuke.Text_Knob('',''))
	
	node['note_font'].setValue('bold')
	node['note_font_size'].setValue(100)
	node['tile_color'].setValue(2047999)
	node['hide_input'].setValue(True)

	node.showControlPanel(forceFloat=True)
	return node




#-------------------------------------------------------------------------------
#-Button Functions
#-------------------------------------------------------------------------------




def add_driver(knobtype):
	"""Add a set driver knobs
	@knobtype: (str) Nuke Knob Type
	"""
	try:	
		dr_no = int(max([find_digit(k) for k in nuke.thisNode().knobs() if k.startswith('dr')]) + 1)
	except Exception as e:
		nuke.warning(e)
		dr_no = 0

	label = nuke.getInput('Label this Driver')	
	if label: 
		k_this_name = 'dr%02d_%s' % (dr_no, label)
		k_this = eval("nuke.{}('')".format(knobtype))
		k_this.setName(k_this_name)
		k_this.setLabel(label)
		k_this.setFlag(nuke.STARTLINE)

		k_set_driven = nuke.PyScript_Knob('dr%02ddriven' % dr_no, STR_SETDRIVEN)
		k_set_driven.setCommand(STR_CMD_SETUP.format("set_driven('%s')" % k_this_name))
		k_set_driven.setTooltip(k_this_name)
		k_set_driven.clearFlag(nuke.STARTLINE)
		k_list_driven = nuke.PyScript_Knob('dr%02dlist' % dr_no, STR_LISTDRIVEN)
		k_list_driven.clearFlag(nuke.STARTLINE)
		k_list_driven.setCommand(STR_CMD_SETUP.format("show_list_driven('%s')" % k_this_name))
		k_list_driven.setTooltip(k_this_name)

		n = nuke.thisNode()
		n.addKnob(k_this)
		n.addKnob(k_set_driven)
		n.addKnob(k_list_driven)


def set_driven(driver_name):
	"""set the driven node.knob with selected nodes
	@driver_name: (str) Name of the driver knob to set expression with
	"""

	node_driver = nuke.thisNode()
	knob_driver = nuke.thisKnob().tooltip()
	driver_type = node_driver.knob(knob_driver).Class()

	with nuke.root():
		nodes_driven = nuke.selectedNodes()
		if node_driver in nodes_driven:
			nodes_driven.remove(node_driver)
	
	if nodes_driven == []:
		nuke.message("Select A Node in DAG")
	else:
		for n in nodes_driven:
			ls_knobs = [k for k in n.knobs() if n.knob(k).Class() in CLASS_EQ[driver_type]]
			ls_knobs = filter_knobs(ls_knobs)
			print(ls_knobs)

			# UI
			panel = nuke.Panel(n.name())
			panel.addEnumerationPulldown('knob to drive: ', ' '.join(ls_knobs))
			panel.addBooleanCheckBox('Invert', False)
			if panel.show():
				k_sel = panel.value('knob to drive: ')
				k_inv = panel.value('Invert')
				if k_sel:
					# Expression string
					str_expr = '%s.%s' % (node_driver.name(), knob_driver)
					str_expr = '1-(%s)' % (str_expr) if k_inv else str_expr
					# set Value
					n.knob(k_sel).setValue(node_driver[knob_driver].value())
					# Add Expression
					n.knob(k_sel).setExpression(str_expr)
					# Visual Labelling
					n.knob('label').setValue(node_driver.knob(driver_name).label())
					n.knob('note_font').setValue('Bold')

					print('%s > %s' % (k_sel, str_expr))

					append_driven_knob(node_driver.knob(knob_driver), n.name(), k_sel)


def show_list_driven(driver_name):
	"""show the list of driven node.knob
	@driver_name: (str) Name of the driver knob to set expression with
	return: (list of knobs) list of node.knob that this driver knob is driving
	"""
	this_node = nuke.thisNode()
	driver_knob = this_node.knob(driver_name)

	# Finall nodes expression linked to Master_Driver
	ls_dep_nodes = this_node.dependent(nuke.EXPRESSIONS)
	ls_dep_knobs = []
	
	for n in ls_dep_nodes:
		# Find all knobs that has expression
		_ls_knob_hasExpr = [k for k in n.knobs() if n.knob(k).hasExpression()]
		# Filter knobs that have driver_name in expression
		for k in filter_knobs(_ls_knob_hasExpr):
			_thisExpr = n.knob(k).animation(0).expression()
			if driver_name in _thisExpr: ls_dep_knobs.append('%s.%s' % (n.name(), k))

	driver_knob.setTooltip('\n'.join(ls_dep_knobs))	
	print("%s is driving %s" % (driver_name, ls_dep_knobs))

	KNOB_LIST_WIDGET.run(driver_knob, ls_dep_knobs)

	return ls_dep_knobs


def sync_list_driven():
	"""sync driven list of each driver knob"""

	print("sync driven list of each driver knob")	




#-------------------------------------------------------------------------------
#-Supportin Functions
#-------------------------------------------------------------------------------



def append_driven_knob(knob_driver, node_driven, knob_driven):
	"""append node_driven.knob_driven to knob_driver's tooltip
	@knob_driver: (knob) driver knob object
	@node_driven: (str) name of the node being driven
	@knob_driven: (str) name of the knob being driven
	"""
	new_entry = '%s.%s' % (node_driven, knob_driven)
	ls = knob_driver.tooltip().split('\n')
	ls.append(new_entry)
	ls = sorted(list(dict.fromkeys(ls)))
	try: ls.remove('')
	except: pass
	knob_driver.setTooltip('\n'.join(ls))
	

def build_driver_types(driver_type, node, newline=False):
	"""Build Driver buttons
	@driver_type: (str) driver type of this node
	@node: (node) the node to add knob
	@newline=False: (bool) if the node create on a newline
	"""

	k_this = nuke.PyScript_Knob('dt_%s' % driver_type, STR_PLUS.format(driver_type))
	k_this.setCommand(STR_CMD_SETUP.format("add_driver('%s')" % DIR_TYPES[driver_type]))
	k_this.setTooltip(DIR_TYPES[driver_type])
	if not newline: k_this.clearFlag(nuke.STARTLINE)
	else: k_this.setFlag(nuke.STARTLINE)
	node.addKnob(k_this)
	print("+%s" % k_this.name())


def find_digit(k):
	"""return interger from knob name
	@k: (str) Driven Knob Name with digit
	return: (int) Integer from Knob name
	"""

	return int(RE_D.search(k).group())


def filter_knobs(ls_knobs):
	"""filter out unwanted layers
	@ls_knobs: (list of knob names)
	return: ls_knobs
	"""
	f = ['xpos', 'indicators', 'lifetimeEnd', 'ypos', 'postage_stamp_frame', 'lifetimeStart', 'note_font_size', 'note_font', 'note_font_color', 'enable']
	return [l for l in ls_knobs if l not in f]
		

# def get_driven_knob(driver):
# 	"""nuke panel to get knob to drive with driver
# 	@driver: (knob) Driver Knob
# 	return: (knob) knob driven
# 	"""




#-------------------------------------------------------------------------------
#-UI
#-------------------------------------------------------------------------------




class DrivenKnobListWidget(QtWidgets.QWidget):
	"""A list widget to display knobs that are driven by given driver knob
	Double-clicked on the item to focus"""
	def __init__(self):
		super(DrivenKnobListWidget,self).__init__()
		self.label = QtWidgets.QLabel()
		self.list_widget = QtWidgets.QListWidget()
		self.list_widget.itemDoubleClicked.connect(self.focus_node)
		self.list_widget.itemEntered.connect(self.open_panel)
		self.list_widget.setToolTip("Double-Click to Focus node in DAG")
		self.tile_color = QtWidgets.QPushButton("Pick Colour")
		# self.tile_color.clicked.connect(self.pick_color)

		self.layout = QtWidgets.QVBoxLayout()
		self.setLayout(self.layout)
		self.layout.addWidget(self.label)
		self.layout.addWidget(self.list_widget)

		self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.WindowCloseButtonHint)
		self.setWindowTitle("Driven Knob List")
	
	def run(self, k_driver, ls_dep_knobs):
		"""Run and Display
		@k_driver: (knob obj) driver knob
		@ls_dep_knobs: (list of str) list of driven knobs in node.knob format
		"""

		self.label.setText(k_driver.label())
		self.list_widget.addItems(ls_dep_knobs)
		self.show()

	def focus_node(self, item):
		"""focus the node in dag"""
		node, knob = item.text().split('.')
		centre = (nuke.toNode(node).xpos(), nuke.toNode(node).ypos())
		nuke.zoom(2.0, centre)

	def open_panel(self, item):
		"""Opens the property panel of this item"""
		node, knob = item.text().split('.')
		nuke.toNode(node).showControlPanel()
	
	# def pick_color(self):
	# 	"""open nuke colour picker to color nodes"""
	# 	col = nuke.getColor()
	# 	ls_nodes = self.list_widget.items()



KNOB_LIST_WIDGET = DrivenKnobListWidget()


#-------------------------------------------------------------------------------
#-Wrapping
#-------------------------------------------------------------------------------




def KnobDriver(): get_master_driver()