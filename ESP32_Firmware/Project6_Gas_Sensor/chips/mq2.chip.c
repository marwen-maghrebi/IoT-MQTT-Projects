// Wokwi Custom Chip
#include "wokwi-api.h"
#include <stdio.h>
#include <stdlib.h>

typedef struct {
  pin_t pin_a0;
  pin_t pin_d0;
  pin_t pin_vcc;
  pin_t pin_gnd;
  uint32_t gas_attr;
} chip_state_t;

static void chip_timer_event(void *user_data);

void chip_init() {
  chip_state_t *chip = malloc(sizeof(chip_state_t));
  
  chip->pin_a0 = pin_init("A0", ANALOG);
  chip->pin_d0 = pin_init("D0", OUTPUT_LOW);
  chip->pin_vcc = pin_init("VCC", INPUT_PULLDOWN);
  chip->pin_gnd = pin_init("GND", INPUT_PULLUP);
  
  chip->gas_attr = attr_init("gas", 0);
  
  const timer_config_t timer_config = {
    .callback = chip_timer_event,
    .user_data = chip
  };
  timer_t timer_id = timer_init(&timer_config);
  timer_start(timer_id, 1000, true);
}

void chip_timer_event(void *user_data) {
  chip_state_t *chip = (chip_state_t*)user_data;
  
  float gas_percent = attr_read_float(chip->gas_attr);
  float gas_ppm = 300 + (gas_percent * 7); // 0-100% → 300-1000ppm
  
  // Same voltage output as before (0-100% → 0-5V)
  float voltage = (gas_percent / 100.0) * 5.0;
  
  if (pin_read(chip->pin_vcc)) {  // Fixed: Added missing parenthesis
    pin_dac_write(chip->pin_a0, voltage);
    printf("Gas: %.1f%% (%.0f ppm), Voltage: %.2fV\n", gas_percent, gas_ppm, voltage);
  }
}