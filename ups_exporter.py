import time
import struct
import os
import smbus2
from gpiozero import Button
from prometheus_client import start_http_server, Gauge

PORT = int(os.getenv("EXPORTER_PORT", 9101))

ups_battery_gauge = Gauge('ups_battery_capacity_percent', 'UPS Battery Capacity in percent')
ups_voltage_gauge = Gauge('ups_voltage_volts', 'UPS Voltage in volts')
ups_power_gauge = Gauge('ups_external_power_status', 'UPS External Power Status (1 = Normal, 0 = Offline)')

# X120Xハードウェア定数
I2C_ADDRESS = 0x36
PLD_PIN = 6

try:
    bus = smbus2.SMBus(1)
    pld_button = Button(PLD_PIN)
except Exception as e:
    print(f"Hardware initialization error: {e}")
    bus = None
    pld_button = None

def update_metrics():
    if not bus or not pld_button:
        ups_battery_gauge.set(0)
        ups_voltage_gauge.set(0)
        ups_power_gauge.set(0)
        return

    try:
        # 電圧と容量の取得
        voltage_read = bus.read_word_data(I2C_ADDRESS, 2)
        capacity_read = bus.read_word_data(I2C_ADDRESS, 4)
        
        voltage_swapped = struct.unpack("<H", struct.pack(">H", voltage_read))[0]
        voltage = voltage_swapped * 1.25 / 1000 / 16
        
        capacity_swapped = struct.unpack("<H", struct.pack(">H", capacity_read))[0]
        capacity = capacity_swapped / 256
        
        # 外部電源状態の取得（ボタンが押されている状態=0: 電源喪失、それ以外=1: 正常）
        power_status = 0 if pld_button.is_pressed else 1

        # メトリクスの更新
        ups_battery_gauge.set(capacity)
        ups_voltage_gauge.set(voltage)
        ups_power_gauge.set(power_status)

    except Exception as e:
        print(f"Error reading from UPS: {e}")
        ups_battery_gauge.set(0)
        ups_voltage_gauge.set(0)
        ups_power_gauge.set(0)

if __name__ == '__main__':
    start_http_server(PORT)
    while True:
        update_metrics()
        time.sleep(15)