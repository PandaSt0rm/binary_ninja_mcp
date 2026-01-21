# Makefile for Binary Ninja MCP test fixtures
#
# Builds test binaries with debug symbols and minimal optimization
# to ensure reliable analysis by Binary Ninja

CC ?= gcc
CFLAGS = -Wall -Wextra -g -O1 -std=c11
LDFLAGS =

# Output binary name
TARGET = test_binary

# Source files
SOURCES = test_binary.c

# Default target
all: $(TARGET)

$(TARGET): $(SOURCES)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

# Build with no optimization (preserves all variables)
debug: CFLAGS = -Wall -Wextra -g -O0 -std=c11
debug: clean $(TARGET)

# Build stripped (for testing without symbols)
stripped: $(TARGET)
	strip -o $(TARGET)_stripped $(TARGET)

# Build 32-bit version (if cross-compilation is available)
x86: CFLAGS += -m32
x86: LDFLAGS += -m32
x86: clean
	$(CC) $(CFLAGS) -o $(TARGET)_x86 $(SOURCES) $(LDFLAGS)

# Clean build artifacts
clean:
	rm -f $(TARGET) $(TARGET)_stripped $(TARGET)_x86

# Verify the binary was built correctly
verify: $(TARGET)
	@echo "=== Binary Info ==="
	@file $(TARGET)
	@echo ""
	@echo "=== Symbols (first 20) ==="
	@nm $(TARGET) | head -20
	@echo ""
	@echo "=== Strings containing 'UNIQUE' ==="
	@strings $(TARGET) | grep UNIQUE || true
	@echo ""
	@echo "=== Sections ==="
	@objdump -h $(TARGET) | head -30
	@echo ""
	@echo "Build successful!"

.PHONY: all debug stripped x86 clean verify
