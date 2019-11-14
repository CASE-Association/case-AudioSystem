/**
 * Copyright (C) 2012 Analog Devices, Inc.
 *
 * THIS SOFTWARE IS PROVIDED BY ANALOG DEVICES "AS IS" AND ANY EXPRESS OR
 * IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, NON-INFRINGEMENT,
 * MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
 *
 **/

/* ====================================================================
 * 2018-08-05:  Modified version for debugging the TCP1701 interface.
 * ==================================================================== */

#include <stdio.h>
#include <stdlib.h>
#include <stddef.h>
#include <unistd.h>
#include <errno.h>
#include <string.h>
#include <time.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netdb.h>
#include <arpa/inet.h>
#include <sys/wait.h>
#include <fcntl.h>
#include <stdbool.h>

#include "sigma_tcp.h"

#include <netinet/in.h>
#include <net/if.h>
#include <netinet/if_ether.h>
#include <sys/ioctl.h>

static void addr_to_str(const struct sockaddr *sa, char *s, size_t maxlen)
{
	switch(sa->sa_family) {
	case AF_INET:
		inet_ntop(AF_INET, &(((struct sockaddr_in *)sa)->sin_addr),
				s, maxlen);
		break;
	case AF_INET6:
		inet_ntop(AF_INET6, &(((struct sockaddr_in6 *)sa)->sin6_addr),
				s, maxlen);
		break;
	default:
		strncpy(s, "Unkown", maxlen);
		break;
	}
}

static int show_addrs(int sck)
{
	char buf[256];
	char ip[INET6_ADDRSTRLEN];
	struct ifconf ifc;
	struct ifreq *ifr;
	unsigned int i, n;
	int ret;

	ifc.ifc_len = sizeof(buf);
	ifc.ifc_buf = buf;
	ret = ioctl(sck, SIOCGIFCONF, &ifc);
	if (ret < 0) {
		perror("ioctl(SIOCGIFCONF)");
		return 1;
	}

	ifr = ifc.ifc_req;
	n = ifc.ifc_len / sizeof(struct ifreq);

	printf("IP addresses:\n");

	for (i = 0; i < n; i++) {
		struct sockaddr *addr = &ifr[i].ifr_addr;

		if (strcmp(ifr[i].ifr_name, "lo") == 0)
			continue;

		addr_to_str(addr, ip, INET6_ADDRSTRLEN);
		printf("%s: %s\n", ifr[i].ifr_name, ip);
	}

	return 0;
}


static void *get_in_addr(struct sockaddr *sa)
{
    if (sa->sa_family == AF_INET)
		return &(((struct sockaddr_in*)sa)->sin_addr);

	return &(((struct sockaddr_in6*)sa)->sin6_addr);
}


/* 
 * Debug functions for ADAU1701. 
 *
 * ADAU1701 Address space: 
 *     0x0000 - 0x03ff  :  Parameter RAM     (4 bytes per word, 5.23 data)
 *     0x0400 - 0x07ff  :  Program RAM       (5 bytes per word, instructions)
 *     0x0800 - 0x0827  :  Control registers (1-5 bytes per register)
 */

static uint8_t debug_param_ram[1024 * 4];  /* 0x0000 - 0x03ff  =  1024 parameters   @ 4 byte */
static uint8_t debug_prog_ram[1024 * 5];   /* 0x0400 - 0x07ff  =  1024 instructions @ 5 byte */

typedef struct _debug_ctrl_regs {
        uint8_t interface0[4];                   /* 0x0800 */
        uint8_t interface1[4];                   /* 0x0801 */
        uint8_t interface2[4];                   /* 0x0802 */
        uint8_t interface3[4];                   /* 0x0803 */
        uint8_t interface4[4];                   /* 0x0804 */
        uint8_t interface5[4];                   /* 0x0805 */
        uint8_t interface6[4];                   /* 0x0806 */
        uint8_t interface7[4];                   /* 0x0807 */
        uint8_t gpio_pin_setting[2];             /* 0x0808 */
        uint8_t aux_adc_data0[2];                /* 0x0809 */
        uint8_t aux_adc_data1[2];                /* 0x080a */
        uint8_t aux_adc_data2[2];                /* 0x080b */
        uint8_t aux_adc_data3[2];                /* 0x080c */
        uint8_t reserved0[5];                    /* 0x080d */
        uint8_t reserved1[5];                    /* 0x080e */
        uint8_t reserved2[5];                    /* 0x080f */
        uint8_t safeload_data0[5];               /* 0x0810 */
        uint8_t safeload_data1[5];               /* 0x0811 */
        uint8_t safeload_data2[5];               /* 0x0812 */
        uint8_t safeload_data3[5];               /* 0x0813 */
        uint8_t safeload_data4[5];               /* 0x0814 */
        uint8_t safeload_addr0[2];               /* 0x0815 */
        uint8_t safeload_addr1[2];               /* 0x0816 */
        uint8_t safeload_addr2[2];               /* 0x0817 */
        uint8_t safeload_addr3[2];               /* 0x0818 */
        uint8_t safeload_addr4[2];               /* 0x0819 */
        uint8_t data_capture0[2];                /* 0x081a */  /* write: 2 bytes address, read: 3 bytes data 5.23 */
        uint8_t data_capture1[2];                /* 0x081b */  /* write: 2 bytes address, read: 3 bytes data 5.23 */
        uint8_t dsp_core_control[2];             /* 0x081c */
        uint8_t reserved3[1];                    /* 0x081d */
        uint8_t serial_output_control[2];        /* 0x081e */
        uint8_t serial_input_control[1];         /* 0x081f */
        uint8_t mp_pin_config0[3];               /* 0x0820 */
        uint8_t mp_pin_config1[3];               /* 0x0821 */
        uint8_t aux_adc_and_power_control[2];    /* 0x0822 */
        uint8_t reserved4[2];                    /* 0x0823 */
        uint8_t aux_adc_enable[2];               /* 0x0824 */
        uint8_t reserved5[2];                    /* 0x0825 */
        uint8_t oscillator_power_down[2];        /* 0x0826 */
        uint8_t dac_setup[2];                    /* 0x0827 */	
        /* fill up to 256 bytes */
        uint8_t _filler[136];
    }
    __attribute__ ((__packed__))    t_debug_ctrl_regs;


static t_debug_ctrl_regs debug_ctrl_regs;        /* memory area (struct) to save/return control register data */

                                                 /* byte offset into t_debug_ctrl_regs struct based on registter address (- 0x800) */
                                                  
static  unsigned int debug_ctrl_regs_offsets[] = {
        offsetof(t_debug_ctrl_regs, interface0),                   /*   0 */
        offsetof(t_debug_ctrl_regs, interface1),                   /*   4 */
        offsetof(t_debug_ctrl_regs, interface2),                   /*   8 */
        offsetof(t_debug_ctrl_regs, interface3),                   /*  12 */
        offsetof(t_debug_ctrl_regs, interface4),                   /*  16 */
        offsetof(t_debug_ctrl_regs, interface5),                   /*  20 */
        offsetof(t_debug_ctrl_regs, interface6),                   /*  24 */
        offsetof(t_debug_ctrl_regs, interface7),                   /*  28 */
        offsetof(t_debug_ctrl_regs, gpio_pin_setting),             /*  32 */
        offsetof(t_debug_ctrl_regs, aux_adc_data0),                /*  34 */
        offsetof(t_debug_ctrl_regs, aux_adc_data1),                /*  36 */
        offsetof(t_debug_ctrl_regs, aux_adc_data2),                /*  38 */
        offsetof(t_debug_ctrl_regs, aux_adc_data3),                /*  40 */
        offsetof(t_debug_ctrl_regs, reserved0),                    /*  42 */
        offsetof(t_debug_ctrl_regs, reserved1),                    /*  47 */
        offsetof(t_debug_ctrl_regs, reserved2),                    /*  52 */
        offsetof(t_debug_ctrl_regs, safeload_data0),               /*  57 */
        offsetof(t_debug_ctrl_regs, safeload_data1),               /*  62 */
        offsetof(t_debug_ctrl_regs, safeload_data2),               /*  67 */
        offsetof(t_debug_ctrl_regs, safeload_data3),               /*  72 */
        offsetof(t_debug_ctrl_regs, safeload_data4),               /*  77 */
        offsetof(t_debug_ctrl_regs, safeload_addr0),               /*  82 */
        offsetof(t_debug_ctrl_regs, safeload_addr1),               /*  84 */
        offsetof(t_debug_ctrl_regs, safeload_addr2),               /*  86 */
        offsetof(t_debug_ctrl_regs, safeload_addr3),               /*  88 */
        offsetof(t_debug_ctrl_regs, safeload_addr4),               /*  90 */
        offsetof(t_debug_ctrl_regs, data_capture0),                /*  92 */
        offsetof(t_debug_ctrl_regs, data_capture1),                /*  94 */
        offsetof(t_debug_ctrl_regs, dsp_core_control),             /*  96 */
        offsetof(t_debug_ctrl_regs, reserved3),                    /*  98 */
        offsetof(t_debug_ctrl_regs, serial_output_control),        /*  99 */
        offsetof(t_debug_ctrl_regs, serial_input_control),         /* 101 */
        offsetof(t_debug_ctrl_regs, mp_pin_config0),               /* 102 */
        offsetof(t_debug_ctrl_regs, mp_pin_config1),               /* 105 */
        offsetof(t_debug_ctrl_regs, aux_adc_and_power_control),    /* 108 */
        offsetof(t_debug_ctrl_regs, reserved4),                    /* 110 */
        offsetof(t_debug_ctrl_regs, aux_adc_enable),               /* 112 */
        offsetof(t_debug_ctrl_regs, reserved5),                    /* 114 */
        offsetof(t_debug_ctrl_regs, oscillator_power_down),        /* 116 */
        offsetof(t_debug_ctrl_regs, dac_setup),                    /* 118 */
        offsetof(t_debug_ctrl_regs, _filler),                      /* 120 */
    };


static void debug_hex(unsigned int addr, unsigned int len, const uint8_t *data)
{
        unsigned int i;

        for (i = 0; i < len; i++) {
            if (i % 16 == 0) {
                if (i != 0) {
                    printf("\n");
                }
                printf("    |       ");
            }
            printf(" 0x%02x", data[i]);
        }
        printf("\n");
}


static int debug_read(unsigned int addr, unsigned int len, uint8_t *data)
{
	memset(data, 0, len);

        if (addr >= 0x0000 && addr < 0x0400) { 
                /* read from parameter ram */
	        unsigned int offset    = addr*4;                                 /* offset into parameter ram when treated as byte array */
                unsigned int max_bytes = sizeof(debug_param_ram) - offset;
                unsigned int n_bytes   = (len > max_bytes) ? max_bytes : len;

                memcpy(data, ((uint8_t *) debug_param_ram) + offset, n_bytes);

                printf("    +--- debug_read parameter data: addr = 0x%04x, bytes = %d\n", addr, len);
                debug_hex(addr, len, data);
                printf("    +---\n");
                return 0;
        }

        if (addr >= 0x0400 && addr < 0x0800) { 
                /* read from program ram */
	        unsigned int offset    = addr*5;                                 /* offset into program ram when treated as byte array */
                unsigned int max_bytes = sizeof(debug_prog_ram) - offset;
                unsigned int n_bytes   = (len > max_bytes) ? max_bytes : len;

                memcpy(data, ((uint8_t *) debug_prog_ram) + offset, n_bytes);

                printf("    +--- debug_read program data: addr = 0x%04x, bytes = %d\n", addr, len);
                debug_hex(addr, len, data);
                printf("    +---\n");

                return 0;
        }

        if (addr >= 0x0800 && addr <= 0x0827) {
                /* read from control register(s) */
	        unsigned int offset    = debug_ctrl_regs_offsets[addr - 0x800];  /* offset of register data in debug_ctrl_regs when treated as byte array */
                unsigned int max_bytes = sizeof(debug_ctrl_regs) - offset;
                unsigned int n_bytes   = (len > max_bytes) ? max_bytes : len;
            
                memcpy(data, ((uint8_t *) (&debug_ctrl_regs)) + offset, n_bytes);

                printf("    +--- debug_read register data: addr = 0x%04x, bytes = %d\n", addr, len);
                debug_hex(addr, len, data);
                printf("    +---\n");

                return 0;
        }

        printf("    +--- debug_read !! address out-of-bounds !! : addr = 0x%04x, bytes = %d\n", addr, len);
        debug_hex(addr, len, data);
        printf("    +---\n");

        return 0;
}

static int debug_write(unsigned int addr, unsigned int len, const uint8_t *data)
{
        if (addr >= 0x0000 && addr < 0x0400) { 
                /* write to parameter ram */
	        unsigned int offset    = addr*4;                                 /* offset into parameter ram when treated as byte array */
                unsigned int max_bytes = sizeof(debug_param_ram) - offset;
                unsigned int n_bytes   = (len > max_bytes) ? max_bytes : len;

                memcpy(((uint8_t * )debug_param_ram) + offset, data, n_bytes);

                printf("    +--- debug_write parameter data: addr = 0x%04x, bytes = %d\n", addr, len);
                debug_hex(addr, len, data);
                printf("    +---\n");

                return 0;
        }

        if (addr >= 0x0400 && addr < 0x0800) { 
                /* write to program ram */
	        unsigned int offset    = addr*5;                                 /* offset into program ram when treated as byte array */
                unsigned int max_bytes = sizeof(debug_prog_ram) - offset;
                unsigned int n_bytes   = (len > max_bytes) ? max_bytes : len;

                memcpy(((uint8_t *) debug_prog_ram) + offset, data, n_bytes);

                printf("    +--- debug_write program data: addr = 0x%04x, bytes = %d\n", addr, len);
                debug_hex(addr, len, data);
                printf("    +---\n");

                return 0;
        }

        if (addr >= 0x0800 && addr <= 0x0827) {
                /* write to control register(s) */
	        unsigned int offset    = debug_ctrl_regs_offsets[addr - 0x800];  /* offset of register data in debug_ctrl_regs when treated as byte array */
                unsigned int max_bytes = sizeof(debug_ctrl_regs) - offset;
                unsigned int n_bytes   = (len > max_bytes) ? max_bytes : len;
            
                memcpy(((uint8_t *) (&debug_ctrl_regs)) + offset, data, n_bytes);

                printf("    +--- debug_write register data: addr = 0x%04x, bytes = %d\n", addr, len);
                debug_hex(addr, len, data);
                printf("    +---\n");
	
                return 0;
        }

        printf("    +--- debug_write !! address out-of-bounds !! : addr = 0x%04x, bytes = %d\n", addr, len);
        debug_hex(addr, len, data);
        printf("    +---\n");

        return 0;
}



#define COMMAND_WRITE    0x09     /* write request (block wite or safeload write) */
#define COMMAND_READ     0x0a     /* read request */ 
#define COMMAND_RESPONSE 0x0b     /* read response packet */


static const struct backend_ops debug_backend_ops = {
	.read = debug_read,
	.write = debug_write,
};

static const struct backend_ops *backend_ops = &debug_backend_ops;


/* Socket handling */

static void handle_connection(int fd)
{
	uint8_t *buf;
	size_t buf_size;
	uint8_t *p;
	unsigned int len;
	unsigned int addr;
/*	unsigned int total_len;*/
	int count, ret;
	char command;

	int         rc;
	int         i;
        time_t      unixtime;
        struct tm  *tm_info;
	char        timestamp[80];

	count = 0;

	buf_size = 256;
	buf = malloc(buf_size);
	if (!buf)
		goto exit;

	p = buf;

	while (1) {
		memmove(buf, p, count);
		p = buf + count;

		ret = read(fd, p, buf_size - count);
		if (ret <= 0)
			break;

		p = buf;

		count += ret;

		while (count >= 8) {
			command = p[0];
/*			total_len = (p[1] << 8) | p[2];*/

			if (command == COMMAND_READ) {
                                len  = (p[4] << 8) | p[5];
				addr = (p[6] << 8) | p[7];

			      	unixtime = time(NULL);
				tm_info  = localtime( &unixtime );
                                strftime(timestamp, 78, "%Y-%m-%d %H:%M:%S", tm_info);

				printf("==== %s ====\n", timestamp);
				printf("READ:     [0..7]  = ");
	        		for (i=0; i<8; i++) { printf(" 0x%02x", p[i]); }
		        	printf("\n");
			        printf("         command :  0x%02x\n",       command);
			        printf("         addr    : %5d (0x%04x)\n", addr, addr);
    			        printf("         len     : %5d (0x%04x)\n", len,  len);

				p += 8;
				count -= 8;

				buf[0] = COMMAND_RESPONSE;
				buf[1] = (0x4 + len) >> 8;
				buf[2] = (0x4 + len) & 0xff;
				buf[3] = backend_ops->read(addr, len, buf + 4);

				rc = write(fd, buf, 4 + len);

				printf("RESPONSE: [0..4]  = ");
	        		for (i=0; i<4; i++) { printf(" 0x%02x", buf[i]); }
		        	printf(" + %i bytes\n", len);
				
				if (rc != 4 + len) {
				        printf("socket write error: weite returned %i, expected %i\n", rc, 4+len);
				}
	
				
			} else if (command == COMMAND_WRITE) {
				/* request header incomplete, fetch next bytes */
				if (count < 10) {
					break;
				}

                                len  = (p[6] << 8) | p[7];
				addr = (p[8] << 8) | p[9];

			      	unixtime = time(NULL);
				tm_info  = localtime( &unixtime );
                                strftime(timestamp, 78, "%Y-%m-%d %H:%M:%S", tm_info);

				printf("==== %s ====\n", timestamp);
				printf("WRITE:    [0..9]  = ");
	        		for (i=0; i<10; i++) { printf(" 0x%02x", p[i]); }
		        	printf("\n");
			        printf("         command :  0x%02x\n",       command);
			        printf("         addr    : %5d (0x%04x)\n", addr, addr);
    			        printf("         len     : %5d (0x%04x)\n", len,  len);

				/* not enough data, fetch next bytes */
				if (count < len + 10) {
					if (buf_size < len + 10) {
						buf_size = len + 10;
						buf = realloc(buf, buf_size);
						if (!buf)
							goto exit;
					}
					break;
				}
				backend_ops->write(addr, len, p + 10);
				p += len + 10;
				count -= len + 10;
			} else {
			      	unixtime = time(NULL);
				tm_info  = localtime( &unixtime );
                                strftime(timestamp, 78, "%Y-%m-%d %H:%M:%S", tm_info);

				printf("==== %s ====\n", timestamp);
				printf("Unknown command: 0x%02x\n", command);
		                p     = buf;
				count = 0;		
			}
		}
	}

exit:
	free(buf);
}

int main(int argc, char *argv[])
{
    int sockfd, new_fd;
	struct addrinfo hints, *servinfo, *p;
    struct sockaddr_storage their_addr;
    socklen_t sin_size;
    int reuse = 1;
    char s[INET6_ADDRSTRLEN];
    int ret;

	if (argc >= 2) {
		if (strcmp(argv[1], "debug") == 0)
			backend_ops = &debug_backend_ops;
		else if (strcmp(argv[1], "i2c") == 0)
			backend_ops = &i2c_backend_ops;
		else if (strcmp(argv[1], "regmap") == 0)
			backend_ops = &regmap_backend_ops;
		else {
			printf("Usage: %s <backend> <backend arg0> ...\n"
				   "Available backends: debug, i2c, regmap\n", argv[0]);
			exit(0);
		}

		printf("Using %s backend\n", argv[1]);
	}

	if (backend_ops->open) {
		ret = backend_ops->open(argc, argv);
		if (ret)
			exit(1);
	}

    memset(&hints, 0, sizeof hints);
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;
    hints.ai_flags = AI_PASSIVE;

	ret = getaddrinfo(NULL, "8086", &hints, &servinfo);
    if (ret != 0) {
        fprintf(stderr, "getaddrinfo: %s\n", gai_strerror(ret));
        return 1;
    }

    for (p = servinfo; p != NULL; p = p->ai_next) {
        if ((sockfd = socket(p->ai_family, p->ai_socktype,
                p->ai_protocol)) == -1) {
            perror("server: socket");
            continue;
        }

        if (setsockopt(sockfd, SOL_SOCKET, SO_REUSEADDR, &reuse,
                sizeof(int)) == -1) {
            perror("setsockopt");
            exit(1);
        }

        if (bind(sockfd, p->ai_addr, p->ai_addrlen) == -1) {
            close(sockfd);
            perror("server: bind");
            continue;
        }

        break;
    }

    if (p == NULL)  {
        fprintf(stderr, "Failed to bind\n");
        return 2;
    }

    freeaddrinfo(servinfo);

    if (listen(sockfd, 0) == -1) {
        perror("listen");
        exit(1);
    }

    printf("Waiting for connections...\n");
	show_addrs(sockfd);

    while (true) {
        sin_size = sizeof their_addr;
        new_fd = accept(sockfd, (struct sockaddr *)&their_addr, &sin_size);
        if (new_fd == -1) {
            perror("accept");
            continue;
        }

        inet_ntop(their_addr.ss_family,
            get_in_addr((struct sockaddr *)&their_addr),
            s, sizeof s);

        printf("New connection from %s\n", s);
		handle_connection(new_fd);
        printf("Connection closed\n");
    }

    return 0;
}
