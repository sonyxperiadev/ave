# Copyright (C) 2013 Sony Mobile Communications AB.
# All rights, including trade secret rights, reserved.

CC      := gcc
CFLAGS  := -Wall -g -O2 -fPIC
LDFLAGS := -g -shared
OBJECTS := fdtx.o

all: libfdtx.so

libfdtx.so: $(OBJECTS)
	$(CC) $(LDFLAGS) $(OBJECTS) -o libfdtx.so

.c.o:
	$(CC) -c $(CFLAGS) $<

clean:
	-$(RM) -f *.o *.so test 

