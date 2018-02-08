CC = gcc
CFLAGS = -g -Wall

all: cernvm_fix_auto_resize

cernvm_fix_auto_resize: cernvm_fix_auto_resize.c
	$(CC) $(CFLAGS) -o $@ $< -ludev

clean:
	rm -f cernvm_fix_auto_resize
