import pcbnew
import wx
import sys
import os
import re

from .jlcpcba_main import *

class JlcpcbaPluginAction(pcbnew.ActionPlugin):
    def defaults(self):
        self.name = "Export JLCPCB PCBA Files"
        self.category = "PCBA"
        self.description = "Create BOM and CPL files for JLCPCBs PCBA Service"
        self.show_toolbar_button = True
        self.icon_file_name = os.path.join(os.path.dirname(__file__), 'jlcpcba.png')

    def Run(self):
        print("Testing")
        try:
            create_pcba()
            wx.MessageDialog(None, "All Done").ShowModal()
        except Exception as e:
            import os
            log_dir = os.environ.get('XDG_RUNTIME_DIR', os.environ['HOME'] )
            log_file = os.path.join(log_dir, 'jlcpcba_run.log')
            with open(log_file, 'wt') as f:
                print(str(e), file=f)
                
            wx.MessageDialog(None, "Failed, check logs").ShowModal()
            raise




