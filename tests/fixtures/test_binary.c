/**
 * test_binary.c - Purpose-built binary for Binary Ninja MCP integration testing
 *
 * This binary is designed to exercise ALL MCP tool functionality with
 * predictable, known features that can be reliably tested.
 *
 * Features exercised:
 * - Multiple functions (list_methods, search_functions_by_name)
 * - Decompilation and disassembly (decompile_function, fetch_disassembly, get_il)
 * - Stack frame variables (get_stack_frame_vars, rename_single_variable, retype_variable)
 * - Comments (set_comment, get_comment, delete_comment, set/get/delete_function_comment)
 * - Strings (list_strings, list_strings_filter, list_all_strings)
 * - Data items (hexdump_address, hexdump_data, get_data_decl, list_data_items)
 * - Types (define_types, declare_c_type, get_user_defined_type, list_local_types, search_types)
 * - Cross-references (get_xrefs_to, get_xrefs_to_field, get_xrefs_to_struct, etc.)
 * - Imports/Exports (list_imports, list_exports)
 * - Segments/Sections (list_segments, list_sections)
 * - Entry points (get_entry_points)
 * - Function operations (rename_function, set_function_prototype, make_function_at)
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

/* ============================================================================
 * SECTION: User-defined types for type system testing
 * Tests: define_types, declare_c_type, get_user_defined_type, list_local_types,
 *        search_types, get_type_info, get_xrefs_to_type
 * ============================================================================ */

/* Enum for testing enum xrefs */
typedef enum {
    STATUS_OK = 0,
    STATUS_ERROR = 1,
    STATUS_PENDING = 2,
    STATUS_TIMEOUT = 3
} StatusCode;

/* Struct for testing struct field xrefs */
typedef struct {
    int32_t id;
    char name[32];
    StatusCode status;
    uint32_t flags;
} TestRecord;

/* Nested struct for complex type testing */
typedef struct {
    TestRecord record;
    void *data;
    size_t data_size;
    struct {
        uint8_t priority;
        uint8_t reserved[3];
    } metadata;
} TestContainer;

/* Union for testing union xrefs */
typedef union {
    uint32_t as_u32;
    int32_t as_i32;
    float as_float;
    uint8_t as_bytes[4];
} ValueUnion;

/* Function pointer typedef */
typedef int (*ProcessCallback)(TestRecord *record, void *context);

/* ============================================================================
 * SECTION: Global data for data analysis testing
 * Tests: hexdump_data, get_data_decl, list_data_items, rename_data
 * ============================================================================ */

/* Global strings for string testing */
const char *g_test_string_ptr = "Global string pointer for testing";
const char g_test_string_array[] = "Global string array for testing";
static const char s_static_string[] = "Static string in data section";

/* Unique strings for filter testing */
const char *g_unique_marker_alpha = "UNIQUE_MARKER_ALPHA_12345";
const char *g_unique_marker_beta = "UNIQUE_MARKER_BETA_67890";

/* Global numeric data */
uint32_t g_global_counter = 0x12345678;
int32_t g_signed_value = -42;
uint64_t g_large_value = 0xDEADBEEFCAFEBABE;

/* Global struct instance */
TestRecord g_global_record = {
    .id = 1001,
    .name = "GlobalRecord",
    .status = STATUS_OK,
    .flags = 0xFFFF0000
};

/* Global array for data testing */
uint8_t g_byte_array[16] = {
    0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77,
    0x88, 0x99, 0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF
};

/* ============================================================================
 * SECTION: Helper functions for function listing and xref testing
 * Tests: list_methods, search_functions_by_name, get_xrefs_to
 * ============================================================================ */

/**
 * Simple helper function - tests basic decompilation
 * Function has: local variables, arithmetic, control flow
 */
int helper_add(int a, int b) {
    int result = a + b;
    return result;
}

/**
 * Helper with multiple local variables - tests stack frame analysis
 */
int helper_calculate(int x, int y, int z) {
    int temp1 = x * 2;
    int temp2 = y * 3;
    int temp3 = z * 4;
    int sum = temp1 + temp2 + temp3;
    return sum;
}

/**
 * String manipulation function - tests string xrefs
 */
void helper_print_string(const char *prefix) {
    printf("%s: %s\n", prefix, g_test_string_ptr);
}

/**
 * Function using structs - tests struct field xrefs
 */
void helper_init_record(TestRecord *record, int32_t id, const char *name) {
    record->id = id;
    strncpy(record->name, name, sizeof(record->name) - 1);
    record->name[sizeof(record->name) - 1] = '\0';
    record->status = STATUS_PENDING;
    record->flags = 0;
}

/**
 * Function using enum values - tests enum xrefs
 */
const char *helper_status_to_string(StatusCode status) {
    switch (status) {
        case STATUS_OK:      return "OK";
        case STATUS_ERROR:   return "ERROR";
        case STATUS_PENDING: return "PENDING";
        case STATUS_TIMEOUT: return "TIMEOUT";
        default:             return "UNKNOWN";
    }
}

/**
 * Function using union - tests union xrefs
 */
void helper_dump_value(ValueUnion *value) {
    printf("U32: 0x%08X, I32: %d, Float: %f\n",
           value->as_u32, value->as_i32, value->as_float);
    printf("Bytes: %02X %02X %02X %02X\n",
           value->as_bytes[0], value->as_bytes[1],
           value->as_bytes[2], value->as_bytes[3]);
}

/* ============================================================================
 * SECTION: Static functions for testing function visibility
 * ============================================================================ */

/**
 * Static function - tests function visibility in exports
 */
static int static_helper(int value) {
    return value * value;
}

/**
 * Another static function with more complexity
 */
static void static_process_data(uint8_t *data, size_t len) {
    for (size_t i = 0; i < len; i++) {
        data[i] ^= 0x55;  /* Simple XOR transformation */
    }
}

/* ============================================================================
 * SECTION: Complex functions for IL and decompilation testing
 * Tests: get_il (hlil/llil/mlil, ssa), decompile_function, fetch_disassembly
 * ============================================================================ */

/**
 * Function with loops - tests IL loop detection
 */
int process_loop_simple(int *array, int count) {
    int sum = 0;
    for (int i = 0; i < count; i++) {
        sum += array[i];
    }
    return sum;
}

/**
 * Function with nested loops - tests complex IL
 */
int process_loop_nested(int **matrix, int rows, int cols) {
    int total = 0;
    for (int i = 0; i < rows; i++) {
        for (int j = 0; j < cols; j++) {
            total += matrix[i][j];
        }
    }
    return total;
}

/**
 * Function with conditionals - tests IL branching
 */
int process_conditional(int value, int threshold) {
    int result;
    if (value > threshold) {
        result = value - threshold;
    } else if (value < -threshold) {
        result = value + threshold;
    } else {
        result = 0;
    }
    return result;
}

/**
 * Function with switch statement - tests IL switch handling
 */
int process_switch(int opcode, int operand) {
    int result = 0;
    switch (opcode) {
        case 0: result = operand;         break;
        case 1: result = operand + 1;     break;
        case 2: result = operand * 2;     break;
        case 3: result = operand << 2;    break;
        case 4: result = operand >> 1;    break;
        case 5: result = ~operand;        break;
        case 6: result = -operand;        break;
        case 7: result = operand & 0xFF;  break;
        default: result = -1;             break;
    }
    return result;
}

/**
 * Function with many local variables - tests stack frame vars
 */
__attribute__((noinline))
int process_many_locals(int input) {
    volatile int var_a = input + 1;
    volatile int var_b = input + 2;
    volatile int var_c = input + 3;
    volatile int var_d = input + 4;
    volatile int var_e = input + 5;
    volatile int var_f = var_a + var_b;
    volatile int var_g = var_c + var_d;
    volatile int var_h = var_e + var_f;
    volatile int var_result = var_g + var_h;
    volatile int *sink = &var_a;
    *sink = *sink + 0;
    return var_result;
}

/* ============================================================================
 * SECTION: Functions using containers - tests nested struct xrefs
 * ============================================================================ */

/**
 * Function working with TestContainer - tests nested struct access
 */
int process_container(TestContainer *container) {
    if (!container || !container->data) {
        return -1;
    }

    /* Access nested struct fields for xref testing */
    container->record.status = STATUS_OK;
    container->metadata.priority = 5;

    /* Process data */
    static_process_data(container->data, container->data_size);

    return container->record.id;
}

/**
 * Function that allocates and initializes a container
 */
TestContainer *create_container(int32_t id, const char *name, size_t data_size) {
    TestContainer *container = malloc(sizeof(TestContainer));
    if (!container) {
        return NULL;
    }

    helper_init_record(&container->record, id, name);
    container->data = malloc(data_size);
    container->data_size = data_size;
    container->metadata.priority = 0;
    memset(container->metadata.reserved, 0, sizeof(container->metadata.reserved));

    if (!container->data) {
        free(container);
        return NULL;
    }

    memset(container->data, 0, data_size);
    return container;
}

/**
 * Function that frees a container
 */
void destroy_container(TestContainer *container) {
    if (container) {
        free(container->data);
        free(container);
    }
}

/* ============================================================================
 * SECTION: Callback function - tests function pointer types
 * ============================================================================ */

/**
 * Sample callback implementation
 */
int sample_callback(TestRecord *record, void *context) {
    int *counter = (int *)context;
    if (record->status == STATUS_OK) {
        (*counter)++;
        return 1;
    }
    return 0;
}

/**
 * Function that uses callback - tests function pointer xrefs
 */
int process_with_callback(TestRecord *records, int count, ProcessCallback callback, void *context) {
    int processed = 0;
    for (int i = 0; i < count; i++) {
        if (callback(&records[i], context)) {
            processed++;
        }
    }
    return processed;
}

/* ============================================================================
 * SECTION: Exported public API functions
 * Tests: list_exports
 * ============================================================================ */

/**
 * Public API function 1 - explicitly marked for export testing
 */
__attribute__((visibility("default")))
int public_api_function_one(int param) {
    return helper_add(param, g_global_counter);
}

/**
 * Public API function 2
 */
__attribute__((visibility("default")))
int public_api_function_two(const char *name) {
    if (name) {
        helper_print_string(name);
        return strlen(name);
    }
    return 0;
}

/**
 * Public API function 3 - uses multiple internal helpers
 */
__attribute__((visibility("default")))
int public_api_function_three(TestRecord *record) {
    if (!record) return -1;

    const char *status_str = helper_status_to_string(record->status);
    printf("Record %d (%s): %s\n", record->id, record->name, status_str);

    return record->id;
}

/* ============================================================================
 * SECTION: Main entry point
 * Tests: get_entry_points, function_at
 * ============================================================================ */

int main(int argc, char *argv[]) {
    printf("Binary Ninja MCP Test Binary\n");
    printf("============================\n\n");

    /* Use global string to ensure it's in the binary */
    printf("Test string: %s\n", g_test_string_ptr);
    printf("Static string: %s\n", s_static_string);
    printf("Unique marker: %s\n", g_unique_marker_alpha);

    /* Test helper functions */
    int sum = helper_add(10, 20);
    printf("helper_add(10, 20) = %d\n", sum);

    int calc = helper_calculate(1, 2, 3);
    printf("helper_calculate(1, 2, 3) = %d\n", calc);

    /* Test record operations */
    TestRecord record;
    helper_init_record(&record, 42, "TestEntry");
    printf("Record: id=%d, name=%s, status=%s\n",
           record.id, record.name, helper_status_to_string(record.status));

    /* Test value union */
    ValueUnion value;
    value.as_u32 = 0x41424344;
    helper_dump_value(&value);

    /* Test loop functions */
    int array[] = {1, 2, 3, 4, 5};
    int loop_sum = process_loop_simple(array, 5);
    printf("process_loop_simple = %d\n", loop_sum);

    /* Test conditional */
    int cond = process_conditional(100, 50);
    printf("process_conditional(100, 50) = %d\n", cond);

    /* Test switch */
    int sw = process_switch(2, 10);
    printf("process_switch(2, 10) = %d\n", sw);

    /* Test many locals */
    int locals = process_many_locals(1);
    printf("process_many_locals(1) = %d\n", locals);

    /* Test container */
    TestContainer *container = create_container(999, "Container", 64);
    if (container) {
        int cont_result = process_container(container);
        printf("process_container = %d\n", cont_result);
        destroy_container(container);
    }

    /* Test callback */
    TestRecord records[3];
    helper_init_record(&records[0], 1, "First");
    records[0].status = STATUS_OK;
    helper_init_record(&records[1], 2, "Second");
    records[1].status = STATUS_ERROR;
    helper_init_record(&records[2], 3, "Third");
    records[2].status = STATUS_OK;

    int callback_count = 0;
    int callback_result = process_with_callback(records, 3, sample_callback, &callback_count);
    printf("process_with_callback = %d (count=%d)\n", callback_result, callback_count);

    /* Test static helper (ensures it's not optimized away) */
    int sq = static_helper(7);
    printf("static_helper(7) = %d\n", sq);

    /* Access global data to ensure it's referenced */
    printf("Global counter: 0x%08X\n", g_global_counter);
    printf("Global record id: %d\n", g_global_record.id);
    printf("Byte array[0]: 0x%02X\n", g_byte_array[0]);

    /* Use public API functions */
    int api1 = public_api_function_one(100);
    printf("public_api_function_one(100) = %d\n", api1);

    int api2 = public_api_function_two("TestPrefix");
    printf("public_api_function_two length = %d\n", api2);

    g_global_record.status = STATUS_OK;
    int api3 = public_api_function_three(&g_global_record);
    printf("public_api_function_three = %d\n", api3);

    printf("\nAll tests completed successfully!\n");
    return 0;
}
