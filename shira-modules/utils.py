import datetime
import json
import math
from os import path

from PySide6.QtWidgets import QApplication

longest_line2 = -1

class TermColors:
	HEADER = "\033[95m"
	OKBLUE = "\033[94m"
	OKCYAN = "\033[96m"
	OKGREEN = "\033[92m"
	WARNING = "\033[93m"
	FAIL = "\033[91m"
	ENDC = "\033[0m"
	BOLD = "\033[1m"
	UNDERLINE = "\033[4m"

def print_color(color: TermColors, text: str):
	print(f"{color}{text}{TermColors.ENDC}")

def pprint(val, no_null = False):
	"""mediafile-specific pretty print"""
	if not isinstance(val, dict):
		print(val)
		return
	d = {}
	for [k, v] in val.items():
		if isinstance(v, bytes):
			decoded = ""
			try: 
				decoded = v.decode("utf-8")
			except:
				decoded = "<non-utf8 bytes>"
			d[k] = decoded
		elif isinstance(v, datetime.date):
			d[k] = f"date({v.isoformat()})"
		elif v is None:
			if no_null:
				continue
			else:
				d[k] = "null" 
		else:
			try:
				json.dumps(v)
				d[k] = v
			except:
				d[k] = f"{str(type(v))} is/contains non-serializable"
	print(json.dumps(d, indent=2))

def end_path(fp: str, segments = 3):
	parts = fp.split(path.sep)
	return path.sep.join(parts[-segments:])

def progprint(curr: int, total: int, width = 10,  message = "", end = "\r"):
	global longest_line2
	perc_factor = (curr / total)
	scaled_perc = math.floor(width * perc_factor)
	if curr == total:
		scaled_perc = width
		perc_factor = 1
	remainder = width - scaled_perc
	line2 = f" {message}" if message.strip() != "" else ""
	if len(line2) > longest_line2:
		longest_line2 = len(line2)
	len_diff = longest_line2 - len(line2)
	if len_diff > 0: # flush previous line2
		line2 += " " * len_diff
		
	print(f"[{'=' * scaled_perc}{' ' * remainder}] {(perc_factor): 5.0%}{line2}", end=end)