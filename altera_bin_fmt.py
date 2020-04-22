#!/usr/bin/env python3
"""
A library for parsing some Altera/Intel FPGA (R) binary formats.
"""
from struct import Struct, error as struct_error
from collections import namedtuple



class JICReaderException(Exception):
	pass

class JICReader:
	"""
	Altera/Intel FPGA (R) *.jic file reader.
	
	User fields:
		self.headers - list of page headers
	"""
	
	
	def __init__(self, f):
		"""
		Creates class instance for a JIC file.
		@param f - file, opened in binary mode, or file name to open
		"""
		def prepare_fobj():
			if type(f) != str:
				return f
			return open(f, 'rb')
		self.f = prepare_fobj()
		self._parse()
		self._save_static_data
	
	def _save_static_data(self):
		# Header type table
		B = "BIN" # Binary
		S = "STR" # Null-terminated string
		self.HTT = {
			1  : (S, "Software version"),
			2  : (S, "Chip name"),
			3  : (S, "Title <unknown purpose>"),
			27 : (S, "Flash device name"),
			28 : (B, "Firmware <12 bytes unknown header(object declaration), then *.rpd equivalent, EPCS-sized space>"),
			30 : (B, "<Unknown binary>"),
			26 : (B, "<Unknown binary struct, string inside>"),
			8  : (B, "<Small binary, likely checksum>")
			
		}
	
	def _parse(self):
		f = self.f
		jic_rec_hdr_st = Struct('<HI')
		#
		d = f.read(12)
		if d[:3] != b'JIC':
			raise JICReaderException("Magic header 'JIC' not found")
		#
		def read_rec_headers():
			JICPage = namedtuple("JICPage", ["type", "pos", "size"])
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
				page = JICPage(t, pos, size)
				yield page
			# EOF check
			our_pos = f.tell()
			eof_pos = f.seek(0,2)
			if our_pos != eof_pos:
				raise JICReaderException("Parsing pages resulted in falling %i bytes beyond the end of file"%(our_pos-eof_pos))
		self.headers = list(read_rec_headers())
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
		def F(x):
			i,h = x
			return "%i: %s"%(i,h)
		return type(self).__name__ + " of %s\navailable pages:\n"%(self.f.name) + "\n".join(map(F, enumerate(jr.headers)))
	
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
	
	
	
jr=JICReader("/home/ivze/rrd-d/prj/SKMv20/output_files/SKMv20.jic")
