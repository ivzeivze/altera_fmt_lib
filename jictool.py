#!/usr/bin/env python3
from argparse import ArgumentParser, FileType
from altera_fmt_lib import JICReader

parser = ArgumentParser(description="Altera/Intel FPGA (R) *.JIC file manipulation tool")
parser.add_argument("-f", "--file", type=FileType("rb"), required=True, help="JIC file to read")
parser.add_argument("-l", "--list-pages", action="store_true", help="List pages")
parser.add_argument("-n", "--nonstrict", action="store_true", help="Disable some strict parsing checks")
parser.add_argument("-x", "--extract-fw", type=FileType("wb"), help="Extract firmware image to the specified file. This should produce a complete configuration device image in RPD-compatible format.")

args = parser.parse_args()


jr = JICReader(args.file, strict = not args.nonstrict)
#
if args.list_pages:
	print(jr)
#
if args.extract_fw:
	fw = jr.extract_firmware()
	args.extract_fw.write(fw)
	print("Firmware extract: %i bytes saved to %s"%(len(fw), args.extract_fw.name))


