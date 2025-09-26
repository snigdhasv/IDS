APP = dpdk_capture
SRCS = main.c

# Use pkg-config to get the correct DPDK flags
CFLAGS += -O3 $(shell pkg-config --cflags libdpdk)
LDFLAGS += $(shell pkg-config --libs libdpdk)

all: $(APP)

$(APP): $(SRCS)
	$(CC) $(CFLAGS) $(SRCS) -o $@ $(LDFLAGS)

clean:
	rm -f $(APP)


