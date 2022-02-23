CC=gcc
OPTS= -lbluetooth

TARGET=simplescan

default: try-ble.c
	$(CC) try-ble.c -o $(TARGET) $(OPTS)