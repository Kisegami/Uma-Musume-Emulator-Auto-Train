"""
Standalone test for LDOpenGL screenshot method.

Requirements: Windows OS, LDPlayer9 (>= 9.0.78), emulator running
Usage: python -m unity_test.test_ldopengl_screenshot
"""

import ctypes
import os
import subprocess
import time
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np
from PIL import Image

# Configuration
LD_FOLDER = r"J:\LDPlayer\LDPlayer9"
INSTANCE_ID = 0
SERIAL = "emulator-5556"  # Optional: auto-detect instance ID
NUM_SCREENSHOTS = 10
SAVE_SCREENSHOTS = True
SCREENSHOT_OUTPUT_DIR = "unity_test/ldopengl_screenshots"


class LDOpenGLIncompatible(Exception):
    pass


class LDOpenGLError(Exception):
    pass


def bytes_to_str(b: bytes) -> str:
    for encoding in ['utf-8', 'gbk']:
        try:
            return b.decode(encoding)
        except UnicodeDecodeError:
            pass
    return str(b)


@dataclass
class DataLDPlayerInfo:
    index: int
    name: str
    topWnd: int
    bndWnd: int
    sysboot: int
    playerpid: int
    vboxpid: int
    width: int
    height: int
    dpi: int

    def __post_init__(self):
        self.index = int(self.index)
        self.name = bytes_to_str(self.name)
        self.topWnd = int(self.topWnd)
        self.bndWnd = int(self.bndWnd)
        self.sysboot = int(self.sysboot)
        self.playerpid = int(self.playerpid)
        self.vboxpid = int(self.vboxpid)
        self.width = int(self.width)
        self.height = int(self.height)
        self.dpi = int(self.dpi)


class LDConsole:
    def __init__(self, ld_folder: str):
        self.ld_console = os.path.abspath(os.path.join(ld_folder, './ldconsole.exe'))
        if not os.path.exists(self.ld_console):
            raise LDOpenGLIncompatible(f'ldconsole.exe not found: {self.ld_console}')

    def subprocess_run(self, cmd, timeout=10):
        cmd = [self.ld_console] + cmd
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=False)
            stdout, _ = process.communicate(timeout=timeout)
            return stdout
        except FileNotFoundError as e:
            raise LDOpenGLIncompatible(f'Cannot execute {cmd}: {e}')
        except subprocess.TimeoutExpired:
            process.kill()
            return b''

    def list2(self):
        out = []
        data = self.subprocess_run(['list2'])
        for row in data.strip().split(b'\n'):
            row = row.strip()
            if not row:
                continue
            parts = row.split(b',')
            if len(parts) == 10:
                try:
                    out.append(DataLDPlayerInfo(*parts))
                except Exception:
                    pass
        return out


class IScreenShotClass:
    def __init__(self, ptr):
        self.ptr = ptr
        cap_type = ctypes.WINFUNCTYPE(ctypes.c_void_p)
        release_type = ctypes.WINFUNCTYPE(None)
        self.class_cap = cap_type(1, "IScreenShotClass_Cap")
        self.class_release = release_type(2, "IScreenShotClass_Release")

    def cap(self):
        return self.class_cap(self.ptr)

    def __del__(self):
        if hasattr(self, 'class_release'):
            self.class_release(self.ptr)


class LDOpenGLImpl:
    def __init__(self, ld_folder: str, instance_id: int):
        ldopengl_dll = os.path.abspath(os.path.join(ld_folder, './ldopengl64.dll'))
        
        try:
            self.lib = ctypes.WinDLL(ldopengl_dll)
        except OSError as e:
            if not os.path.exists(ldopengl_dll):
                raise LDOpenGLIncompatible(
                    f'ldopengl64.dll not found. Requires LDPlayer >= 9.0.78'
                )
            raise LDOpenGLIncompatible(f'Cannot load DLL: {e}')
        
        self.console = LDConsole(ld_folder)
        self.info = self.get_player_info_by_index(instance_id)
        
        self.lib.CreateScreenShotInstance.restype = ctypes.c_void_p
        instance_ptr = ctypes.c_void_p(
            self.lib.CreateScreenShotInstance(instance_id, self.info.playerpid)
        )
        self.screenshot_instance = IScreenShotClass(instance_ptr)

    def get_player_info_by_index(self, instance_id: int):
        for info in self.console.list2():
            if info.index == instance_id:
                if not info.sysboot:
                    raise LDOpenGLError(f'Instance {instance_id} is not running')
                return info
        raise LDOpenGLError(f'No instance with index {instance_id}')

    def screenshot(self):
        img_ptr = self.screenshot_instance.cap()
        if img_ptr is None:
            raise LDOpenGLError('Empty image pointer')
        
        width, height = self.info.width, self.info.height
        img = ctypes.cast(
            img_ptr, 
            ctypes.POINTER(ctypes.c_ubyte * (height * width * 3))
        ).contents
        return np.ctypeslib.as_array(img).reshape((height, width, 3))

    @staticmethod
    def serial_to_id(serial: str) -> Optional[int]:
        try:
            if ':' in serial:
                port = int(serial.split(':')[1])
                if 5555 <= port <= 5555 + 32:
                    return (port - 5555) // 2
            elif serial.startswith('emulator-'):
                port = int(serial.replace('emulator-', ''))
                if 5554 <= port <= 5554 + 32:
                    return (port - 5554) // 2
        except (ValueError, IndexError):
            pass
        return None


def process_screenshot(image: np.ndarray, orientation: int = 0) -> np.ndarray:
    image = cv2.flip(image, 1 if orientation == 2 else 0)
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def print_stats(label: str, times: list):
    sorted_times = sorted(times)
    print(f"{label}: Min={min(times):.2f}ms, Max={max(times):.2f}ms, "
          f"Avg={sum(times)/len(times):.2f}ms, Median={sorted_times[len(times)//2]:.2f}ms")


def test_ldopengl_screenshot():
    if os.name != 'nt':
        print("ERROR: LDOpenGL only works on Windows!")
        return False
    
    instance_id = INSTANCE_ID
    if SERIAL:
        auto_id = LDOpenGLImpl.serial_to_id(SERIAL)
        if auto_id is not None:
            instance_id = auto_id
    
    print(f"LDOpenGL Screenshot Test")
    print(f"LD_FOLDER: {LD_FOLDER}, Instance ID: {instance_id}, Screenshots: {NUM_SCREENSHOTS}\n")
    
    try:
        ldopengl = LDOpenGLImpl(LD_FOLDER, instance_id)
        print(f"Connected: {ldopengl.info.name} ({ldopengl.info.width}x{ldopengl.info.height})\n")
    except (LDOpenGLIncompatible, LDOpenGLError) as e:
        print(f"ERROR: {e}")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    if SAVE_SCREENSHOTS:
        os.makedirs(SCREENSHOT_OUTPUT_DIR, exist_ok=True)
    
    times = []
    for i in range(NUM_SCREENSHOTS):
        try:
            start = time.perf_counter()
            raw_image = ldopengl.screenshot()
            capture_time = (time.perf_counter() - start) * 1000
            
            start = time.perf_counter()
            processed_image = process_screenshot(raw_image)
            process_time = (time.perf_counter() - start) * 1000
            
            total_time = capture_time + process_time
            times.append({'capture': capture_time, 'process': process_time, 'total': total_time})
            
            print(f"[{i+1}/{NUM_SCREENSHOTS}] Capture: {capture_time:.2f}ms, "
                  f"Process: {process_time:.2f}ms, Total: {total_time:.2f}ms")
            
            if SAVE_SCREENSHOTS:
                Image.fromarray(processed_image).save(
                    os.path.join(SCREENSHOT_OUTPUT_DIR, f"screenshot_{i+1:03d}.png")
                )
        except Exception as e:
            print(f"ERROR: Screenshot {i+1} failed: {e}")
    
    if times:
        capture_times = [t['capture'] for t in times]
        process_times = [t['process'] for t in times]
        total_times = [t['total'] for t in times]
        
        print("\nPerformance Statistics:")
        print_stats("Capture", capture_times)
        print_stats("Process", process_times)
        print_stats("Total", total_times)
        print(f"FPS Estimate: {1000.0 / (sum(total_times)/len(total_times)):.2f} fps")
        
        if SAVE_SCREENSHOTS:
            print(f"\nSaved {len(times)} screenshots to: {SCREENSHOT_OUTPUT_DIR}")
        return True
    else:
        print("ERROR: No successful screenshots captured!")
        return False


if __name__ == "__main__":
    try:
        exit(0 if test_ldopengl_screenshot() else 1)
    except KeyboardInterrupt:
        print("\nTest interrupted.")
        exit(1)
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

