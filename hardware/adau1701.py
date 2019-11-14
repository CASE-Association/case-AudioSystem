#!/usr/bin/env python
#
# Hardware routines for the ADAU1701
# addressing is always done in 16bit

import math
import numpy as np
try:
	from smbus2 import SMBus, i2c_msg,SMBusWrapper
	i2c_available=True
	smb=SMBus(1);
except ImportError:
	i2c_available=False
	smb=None

# ADAU1701 address range
MAXADDRESS=2087
I2C_SLAVEADDR=0x34
COREREG_ADDR=2076
LSB_SIGMA=float(1)/math.pow(2,23)

def float_to_28bit_fixed(f):
	'''
	converts a float to an 28bit fixed point value used in SigmaDSP processors
	'''
	if (f>16-LSB_SIGMA) or (f<-16):
		raise Exception("value {} not in range [-16,16]".format(f))

	# dual complement
	if (f<0):
		f=32+f
	
	# multiply by 2^23, then convert to integer
	f=f*(1<<23)
	return int(f)

def dsp28bit_fixed_to_float(p):
	'''
    converts an 28bit fixed point value used in SigmaDSP processors to a float value
    '''
	f=float(p)/pow(2,23)
	if f>=16:
		f=-32+f
	return f



def addr2memsize(addr):
	if (addr < 1024):
		blocksize=4
	elif (addr < 2048):
		blocksize=5
	elif (addr < 2056):
		blocksize=4
	elif (addr < 2061):
		blocksize=2
	elif (addr < 2069):
		blocksize=5
	elif (addr < 2077):
		blocksize=2
	elif (addr < 2078):
		blocksize=1
	elif (addr < 2079):
		blocksize=2
	elif (addr < 2080):
		blocksize=1
	elif (addr < 2082):
		blocksize=3
	elif (addr < 2088):
		blocksize=2
	else:
		blocksize=1
	return blocksize

def dsp_write_blocks(blocks, verbose=True):
	if not i2c_available:
			print "I2C not available, simulating only"
	for block in blocks:
		addr=block["address"]
		data=block["data"]
		if verbose:
			print "Writing {0} at {1:04X} ({1}), {2} byte".format(block["name"],addr,len(data))
		if i2c_available:
			dsp_write_block(addr,data,verbose)

def dsp_write_block(addr,data,verbose=0):
	# split into blocks, block size depends on the address
	while len(data) > 0:
		blocksize=addr2memsize(addr)
		block=data[0:blocksize]
		if (verbose):
			print addr, block
		dsp_write_small_block(addr,block)
		data=data[blocksize:]
		addr += 1;
		

def dsp_write_small_block(addr,data):
	a1=addr/256
	a0=addr%256

	data.insert(0,a0);
	if smb:
		smb.write_i2c_block_data(I2C_SLAVEADDR,a1,data)
	else:
		print "Simulated I2C write address={} value={}".format(addr,data[1:])
		
def write_param(paramaddr,value):
	# convert to 4 byte representation first
	values=[]
	for _i in range(0,4):
		values.insert(0,int(value%256))
		value/=256
	dsp_write_small_block(paramaddr, values)
		
# generate a full memory dump based on the content parsed from TXBuffer
def memory_map_from_blocks(blocks):
	mem=[0]*(MAXADDRESS+1)
	for block in blocks:
		addr=block["address"]
		data=block["data"]
		# split into blocks, block size depends on the address
		while len(data) > 0:
			blocksize=addr2memsize(addr)
			block=data[0:blocksize]
			mem[addr]=block
			data=data[blocksize:]
			addr += 1;
	return mem


def read_back(H_addr, L_addr):
	dsp_write_small_block(0x081A, [H_addr, L_addr])
	write = i2c_msg.write(I2C_SLAVEADDR, [0x08, 0x1A])
	rd = i2c_msg.read(I2C_SLAVEADDR, 3)
	with SMBusWrapper(1) as bus:
		bus.i2c_rdwr(write, rd)
	'''MSB first, convert from 5.19 to 5.27 format'''
	val = list(rd)
	ret = (np.uint32(np.uint(val[0])) << 24 | np.uint32(val[1]) << 16 | np.uint32(val[2]) << 8 & 0xFFFFFF00)
	ret = (float(ret)/(np.uint32(1) << 27))
	return ret







'''
void readBack(uint8_t dspAddress, uint16_t address, uint16_t capturecount, float *value){

  uint8_t buf[3];
  int32_t word32 = 0;

  buf[0] = capturecount >> 8;
  buf[1] = (uint8_t)capturecount & 0xFF;
  AIDA_WRITE_REGISTER(dspAddress, address, 2, buf);    // readBack operation

  memset(buf, 0, 3);

  AIDA_READ_REGISTER(dspAddress, address, 3, buf);

  word32 = ((uint32_t)buf[0]<<24 | (uint32_t)buf[1]<<16 | (uint32_t)buf[2]<<8)&0xFFFFFF00; // MSB first, convert from 5.19 to 5.27 format

  if(word32==0)
    word32 = 1;

  *value = ((float)word32/((uint32_t)1 << 27)); // I'm converting from 5.27 int32 to maintain sign
}
'''


def main():
	print(read_back(0x00, 0xA6))


if __name__ == '__main__':
	main()
