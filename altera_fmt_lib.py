#!/usr/bin/env python3
"""
A library for parsing some Altera/Intel FPGA (R) binary formats.
"""
from struct import Struct, error as struct_error
from collections import namedtuple
import sys
if sys.version_info < (3,):
	raise Exception("Python version too old")


class AlteraTagException(Exception):
	pass

class AlteraTag:
	"""This class represents our concept of 12 byte binary structures,
	found in JIC's and POF's, SOF's and likely others. Those are
	expected to be tags, placed at the beginning of data blocks.
	
	Likely these are some kind of unique identifiers, that determine,
	which kind data structure resides at the inner layer of abstraction,
	should this need clarification.
	
	I might be completely wrong, however =)
	"""
	
	def __init__(self, buf):
		"""@param buf - 12 byte binary
		"""
		if not (len(buf) == 12 and type(buf) == bytes):
			raise AlteraTagException("Data buffer expected to be 12 bytes binary")
		self.buf = buf
	
	S = Struct("<4sII") # Our hypothesis for the structure. 
	
	def _build_classificator(S):
		return {
			S.pack(b"JIC", 0, 0x08) : "JIC_HEADER",
			S.pack(b"SOF", 0, 0x0B) : "SOF_HEADER",
			S.pack(b"POF", 0x010000, 0x07) : "POF_HEADER",
			S.pack(b"", 0, 0x010800) : "RAW_FIRMWARE"
		}
	classificator = _build_classificator(S)
	
	def list_known_classes():
		l=list(classificator.values())
		l.sort()
		return l
	
	def check_ext_unstrict(self, ext):
		"""Checks the first len(ext) bytes to match specified ext"""
		return self.buf.startswith(ext)
	
	def decode_struct(self):
		"""Decodes binary data according to suggested data structure.
		String field is stripped from zero bytes to the right."""
		x = self.S.unpack(self.buf)
		return (x[0].rstrip(b"\x00"),) + x[1:]

	
	def classify(self):
		"""Makes a lookup of object binary in static list of known types.
		@return one of classes from list_known_classes() or None, if nothing was found."""
		try:
			return self.classificator[self.buf]
		except KeyError:
			return None
	
	def hexdump(self):
		bb=self.buf
		LL = []
		for i in range(3):
			b=bb[4*i:4*i+4]
			LL.append(" ".join(map(lambda i: "%.2x"%(i), b)))
		return "  ".join(LL)
	
	def __repr__(self):
		return "\n".join([
			type(self).__name__,
			"hex: %s"%(self.hexdump()),
			"bin: %s"%(str(self.buf)),
			"Classified as: %s"%(self.classify())
		])


class JICReaderException(Exception):
	pass


class JICReader:
	"""
	Altera/Intel FPGA (R) *.jic file reader.

	User fields:
		self.headers - list of page headers

	Methods throw JICReaderException to identify errors.
	"""

	JICPage = namedtuple("JICPage", ["type", "pos", "size"])

	def __init__(self, f, strict=True):
		"""Creates class instance for a JIC file.
		@param f - file, opened in binary mode, or file name to open
		@param strict - set False to skip some parsing checks
		"""
		def prepare_fobj():
			if type(f) != str:
				return f
			return open(f, 'rb')
		self.f = prepare_fobj()
		self.strict = bool(strict)
		self._parse()

	def _make_static_data():
		# Header type table
		B = "BIN" # Binary
		S = "STR" # Null-terminated string
		htt = {
			1  : (S, "Software version"),
			2  : (S, "Chip name"),
			3  : (S, "Title"),
			27 : (S, "Configuration device name"),
			28 : (B, "Firmware"),
			30 : (B, "<Unknown binary>"),
			26 : (B, "<Unknown binary struct, string inside>"),
			8  : (B, "<Small binary, likely checksum>")
		}
		return htt
	htt = _make_static_data()
	
	def describe_type_id(self, type_id):
		"""Describes page type in human words"""
		try:
			t,desc = self.htt[type_id]
		except KeyError:
			return "<Unknown type id>"
		return "%s %s"%(t,desc) 

	def _parse(self):
		f = self.f
		jic_rec_hdr_st = Struct('<HI')
		#
		root_tag = AlteraTag(f.read(12))
		if self.strict:
			# strict
			def check_rt():
				return root_tag.classify() == "JIC_HEADER"
		else:
			# simplified
			def check_rt():
				return root_tag.check_ext_unstrict(b"JIC")
		if not check_rt():
			raise JICReaderException("Bad root tag.\n"+str(root_tag))
		#
		def read_rec_headers():
			while True:
				data = f.read(jic_rec_hdr_st.size)
				if not data:
					break # reached clean end of file
				try:
					t, size = jic_rec_hdr_st.unpack(data)
				except struct_error as e:
					raise JICReaderException("Stray bytes at the end of file. " + str(e))
				pos = f.tell() # the header - just behind, after we have L bytes of page data
				f.seek(pos + size)
				page = self.JICPage(t, pos, size)
				yield page
			# EOF check
			our_pos = f.tell()
			eof_pos = f.seek(0,2)
			if our_pos != eof_pos:
				raise JICReaderException("Parsing pages resulted in falling %i bytes beyond the end of file"%(our_pos-eof_pos))
		self.headers = list(read_rec_headers())
		#
		def build_typedict():
			D = dict()
			for i,h in enumerate(self.headers):
				if h.type not in D:
					D[h.type] = [i]
				else:
					D[h.type].append(i)
			return D
		# type -> header_id mapping
		self.typedict = build_typedict()

	def __repr__(self):
		def G(h):
			return str(h) + "\n\t└>" + self.describe_type_id(h.type)
		def F(x):
			i,h = x
			return "%i: %s"%(i,G(h))
		return type(self).__name__ + " of %s\navailable pages:\n"%(self.f.name) + "\n".join(map(F, enumerate(self.headers)))

	def read_page(self, hdr):
		"""Reads page data by page structure as found in self.headers"""
		self.f.seek(hdr.pos)
		data = self.f.read(hdr.size)
		if len(data) < hdr.size:
			raise JICReaderException("Can't read full page data")
		return data

	def read_page_by_id(self, i):
		"""Reads a page by offset in self.headers list."""
		return self.read_page(self.headers[i])

	def read_pages_by_type(self, t):
		"""
		Reads all pages of a certain type in order of occurrence
		@param t - type integer code
		@return [bytes], list of binary data strings
		"""
		TD = self.typedict
		if t not in TD:
			return []
		ii = TD[t]
		return [self.read_page_by_id(i) for i in ii]

	def list_types(self):
		"""Returns a list of type codes of pages found in JIC file."""
		tt = list(self.typedict.keys())
		tt.sort()
		return tt

	def extract_firmware(self):
		"""Extracts complete configuration device image, stored in JIC.
		The resulting byte stream is encoded the same way as an RPD
		file (not to be confused with RBF files, those are encoded 
		differently and have a different purpose, see 
		"Bug ID: FB: 514899;" in Intel FPGA Knowledge DB).
			A JIC file does not contain (highly likely) any information
		regarding block allocation, rather it stores an amalgam of
		possible multiple blocks, mixed with unallocated space, denoted
		by 0xff, that is the default post-erase value for at least EPCS 
		flash family.
			FPGA boot loader stream for a valid JIC starts from zero address
		and extends for some arbitrary byte length. After the end of
		boot image 0xff blank bytes are found stuffing the free space.
		However without knowing the original MAP file it is impossible
		to determine, where boot image ends, and where the trailing 
		bytes start, as it is fairly possible (and typical) for a boot
		image to end with some number of 0xff bytes (as seen by 
		analyzing valid RPD-s). FPGA hardware loader engine obviously
		has means to stop at boot loader end, but it's mechanics are 
		beyond our scope of interest. One might be pretty sure, that if
		enough trailing 0xff bytes are copied, the boot loader will 
		function fine.
		"""
		FW_PAGE_ID = 28
		pp = self.read_pages_by_type(FW_PAGE_ID)
		if not (len(pp) == 1 if self.strict else len(pp) != 0):
			raise JICReaderException("%i firmware (code id %i) pages found, this is not OK."%(len(pp), FW_PAGE_ID))
		#
		data = pp[0]
		tag = AlteraTag(data[:12])
		#
		if self.strict:
			if tag.classify() != "RAW_FIRMWARE":
				raise JICReaderException("Tag mismatch, found bad tag: %s"%(tag))
		#
		return data[12:]
