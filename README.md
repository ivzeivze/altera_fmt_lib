# altera_fmt_lib
A library for parsing some Altera/Intel FPGA (R) binary formats.

The purpose of this project is to be able to extract binary firmwares out of Altera/Intel FPGA binary containers.
These containers are pretty simple, a chain of header-offset records.

Currently parsing JIC files is supported. An utility script jictool.py is available, that can extract a RPD compatible image from a given file.

Parsing POF and SOF files *should be* quite similar, according to my findings.

