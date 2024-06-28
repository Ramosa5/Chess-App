import xml.etree.ElementTree as ET
from xml.dom import minidom
import os

class FenXMLDatabase:
    def __init__(self, file_name='fen_notations.xml'):
        self.file_name = file_name
        if not os.path.exists(self.file_name):
            self.create_file()
        else:
            self.tree = ET.parse(self.file_name)
            self.root = self.tree.getroot()

    def create_file(self):
        self.root = ET.Element("FENNotations")
        self.tree = ET.ElementTree(self.root)
        self.tree.write(self.file_name)

    def prettify(self, elem):
        """Return a pretty-printed XML string for the Element."""
        rough_string = ET.tostring(elem, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")

    def add_fen_notation(self, fen_string):
        move = ET.SubElement(self.root, "Move")
        fen = ET.SubElement(move, "FEN")
        fen.text = fen_string
        self.tree.write(self.file_name)

    def clear_file(self):
        self.root.clear()
        self.tree.write(self.file_name)
