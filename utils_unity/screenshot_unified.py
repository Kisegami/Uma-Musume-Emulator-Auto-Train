import os
import json
import ctypes
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from typing import Optional, Union
from PIL import Image, ImageEnhance
import numpy as np
from utils.device import run_adb
from utils.log import log_debug, log_info, log_warning, log_error


class NemuIpcIncompatible(Exception):
    """Raised when Nemu IPC is not available or compatible"""
    pass


class NemuIpcError(Exception):
    """Raised when Nemu IPC operations fail"""
    pass


class NemuIpcCapture:
    """Nemu IPC capture implementation for faster screenshots"""

    def __init__(self, nemu_folder: str, instance_id: int, display_id: int = 0, timeout: float = 1.0, verbose: bool = False):
        self.nemu_folder = nemu_folder
        self.instance_id = instance_id
        self.display_id = display_id
        self.timeout = timeout
        self.verbose = verbose
        self.connect_id = 0
        self.width = 0
        self.height = 0

        # Try to load DLL from possible locations
        candidates = [
            os.path.abspath(os.path.join(nemu_folder, './shell/sdk/external_renderer_ipc.dll')),
            os.path.abspath(os.path.join(nemu_folder, './nx_device/12.0/shell/sdk/external_renderer_ipc.dll')),
        ]
        self.lib = None
        last_err = None
        for dll in candidates:
            if not os.path.exists(dll):
                continue
            try:
                self.lib = ctypes.CDLL(dll)
                break
            except OSError as e:
                last_err = e
                continue
        if self.lib is None:
            raise NemuIpcIncompatible(
                f'Cannot load external_renderer_ipc.dll. Tried: {candidates}. Last error: {last_err}'
            )

        # Function prototypes
        try:
            self.lib.nemu_connect.restype = ctypes.c_int
        except Exception:
            pass
        try:
            self.lib.nemu_disconnect.argtypes = [ctypes.c_int]
            self.lib.nemu_disconnect.restype = ctypes.c_int
        except Exception:
            pass

        self.lib.nemu_capture_display.argtypes = [
            ctypes.c_int, ctypes.c_int, ctypes.c_int,
            ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int), ctypes.c_void_p
        ]
        self.lib.nemu_capture_display.restype = ctypes.c_int

        self._executor = ThreadPoolExecutor(max_workers=1)

    @staticmethod
    def serial_to_id(serial: str) -> Optional[int]:
        """Convert ADB serial to Nemu instance ID"""
        try:
            port = int(serial.split(':')[1])
        except (IndexError, ValueError):
            return None
        index, offset = divmod(port - 16384 + 16, 32)
        offset -= 16
        if 0 <= index < 32 and offset in [-2, -1, 0, 1, 2]:
            return index
        return None

    def _run_with_timeout(self, func, *args, timeout: Optional[float] = None):
        if timeout is None:
            return func(*args)
        fut = self._executor.submit(func, *args)
        try:
            return fut.result(timeout=timeout)
        except TimeoutError:
            fut.cancel()
            raise NemuIpcError('IPC call timeout')

    def connect(self, timeout: Optional[float] = None):
        """Connect to Nemu emulator"""
        if self.connect_id:
            return
        
        # Simple connection - DLL messages will go to console but won't affect GUI
        cid = self.lib.nemu_connect(self.nemu_folder, int(self.instance_id))
        if cid == 0 and timeout is not None:
            folder_bytes = os.fsencode(self.nemu_folder)
            cid = self._run_with_timeout(self.lib.nemu_connect, folder_bytes, int(self.instance_id), timeout=timeout)
        if cid == 0:
            raise NemuIpcError('nemu_connect failed. Check folder path and that emulator is running')
        self.connect_id = int(cid)

    def disconnect(self):
        """Disconnect from Nemu emulator"""
        if not self.connect_id:
            return
        try:
            self.lib.nemu_disconnect(int(self.connect_id))
        finally:
            self.connect_id = 0

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def get_resolution(self, timeout: Optional[float] = None):
        """Get screen resolution"""
        if not self.connect_id:
            self.connect(timeout=timeout)
        w_ptr = ctypes.pointer(ctypes.c_int(0))
        h_ptr = ctypes.pointer(ctypes.c_int(0))
        null = ctypes.c_void_p()
        ret = self._run_with_timeout(
            self.lib.nemu_capture_display,
            int(self.connect_id), int(self.display_id), 0, w_ptr, h_ptr, null,
            timeout=timeout,
        )
        if int(ret) > 0:
            raise NemuIpcError('nemu_capture_display failed in get_resolution')
        self.width = w_ptr.contents.value
        self.height = h_ptr.contents.value

    def screenshot(self, timeout: Optional[float] = None) -> np.ndarray:
        """Take screenshot using Nemu IPC"""
        if not self.connect_id:
            self.connect(timeout=timeout)
        if self.width == 0 or self.height == 0:
            self.get_resolution(timeout=timeout)
        w_ptr = ctypes.pointer(ctypes.c_int(int(self.width)))
        h_ptr = ctypes.pointer(ctypes.c_int(int(self.height)))
        length = int(self.width * self.height * 4)
        pixels = (ctypes.c_ubyte * length)()
        ret = self._run_with_timeout(
            self.lib.nemu_capture_display,
            int(self.connect_id), int(self.display_id), length, w_ptr, h_ptr, ctypes.byref(pixels),
            timeout=timeout,
        )
        if int(ret) > 0:
            raise NemuIpcError('nemu_capture_display failed in screenshot')
        # Build numpy array from ctypes buffer
        arr = np.frombuffer(pixels, dtype=np.uint8)
        arr = arr.reshape((int(self.height), int(self.width), 4))
        return arr


class AdbCapture:
    """ADB capture implementation (existing functionality)"""

    def __init__(self, config: dict):
        self.config = config

    def screenshot(self) -> Image.Image:
        """Take screenshot using ADB"""
        try:
            result = run_adb(['shell', 'screencap'], binary=True, add_input_delay=False)
            if result is None:
                raise Exception("Failed to take screenshot")

            cleaned_result = result.replace(b'\r\n', b'\n')  # Remove carriage returns

            # Parse the header: width (4 bytes), height (4 bytes), format (4 bytes), unknown (4 bytes)
            width = int.from_bytes(cleaned_result[0:4], byteorder='little')
            height = int.from_bytes(cleaned_result[4:8], byteorder='little')

            pixel_data = cleaned_result[16:]  # Skip the header (16 bytes)

            img = Image.frombytes('RGBA', (width, height), pixel_data)
            return img
        except Exception as e:
            log_error(f"Error taking ADB screenshot: {e}")
            raise


class UnifiedScreenshot:
    """Unified screenshot system that can use either ADB or Nemu IPC"""

    def __init__(self):
        self.config = self._load_config()
        self.capture_method = self.config.get('capture_method', 'adb')
        self.nemu_capture = None
        self.adb_capture = None

        # Initialize capture method
        if self.capture_method == 'nemu_ipc':
            try:
                nemu_config = self.config.get('nemu_ipc_config', {})
                self.nemu_capture = NemuIpcCapture(
                    nemu_folder=nemu_config.get('nemu_folder', 'J:\\MuMuPlayerGlobal'),
                    instance_id=nemu_config.get('instance_id', 2),
                    display_id=nemu_config.get('display_id', 0),
                    timeout=nemu_config.get('timeout', 1.0),
                    verbose=False
                )
                # Only print once during initialization, not every screenshot
                if not hasattr(self, '_nemu_initialized'):
                    log_info(f"Initialized Nemu IPC capture with method: {self.capture_method}")
                    log_info("Note: DLL connection messages may appear in console (won't affect GUI)")
                    self._nemu_initialized = True
            except Exception as e:
                log_error(f"Failed to initialize Nemu IPC capture: {e}")
                log_info("Falling back to ADB capture")
                self.capture_method = 'adb'

        if self.capture_method == 'adb':
            self.adb_capture = AdbCapture(self.config.get('adb_config', {}))
            log_info(f"Using ADB capture method: {self.capture_method}")

    def _load_config(self) -> dict:
        """Load configuration from config.json"""
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            log_error(f"Error loading config: {e}")
            return {}

    def take_screenshot(self) -> Image.Image:
        """Take screenshot using the configured capture method"""
        if self.capture_method == 'nemu_ipc' and self.nemu_capture:
            try:
                # Use Nemu IPC capture
                with self.nemu_capture:
                    # Nemu IPC returns RGBA directly - NO conversion needed!
                    rgba_array = self.nemu_capture.screenshot()
                    
                    # Only flip vertically, no color conversion
                    flipped_array = np.flip(rgba_array, axis=0)
                    
                    # Convert to PIL Image
                    img = Image.fromarray(flipped_array, 'RGBA')
                    return img
            except Exception as e:
                log_error(f"Nemu IPC capture failed: {e}")
                log_info("Falling back to ADB capture")
                self.capture_method = 'adb'

        # Fallback to ADB capture
        if self.adb_capture:
            return self.adb_capture.screenshot()
        else:
            # Initialize ADB capture if not already done
            self.adb_capture = AdbCapture(self.config.get('adb_config', {}))
            return self.adb_capture.screenshot()

    def get_screen_size(self) -> tuple:
        """Get screen size"""
        try:
            if self.capture_method == 'nemu_ipc' and self.nemu_capture:
                with self.nemu_capture:
                    self.nemu_capture.get_resolution()
                    return self.nemu_capture.width, self.nemu_capture.height
            else:
                # Fallback to ADB method
                result = run_adb(['shell', 'wm', 'size'])
                if result:
                    if 'Physical size:' in result:
                        size_part = result.split('Physical size:')[1].strip()
                        width, height = map(int, size_part.split('x'))
                        return width, height
                    else:
                        width, height = map(int, result.split('x'))
                        return width, height
                else:
                    # Fallback: take a screenshot and get its size
                    screenshot = self.take_screenshot()
                    return screenshot.size
        except Exception as e:
            log_error(f"Error getting screen size: {e}")
            # Default fallback size
            return 1080, 1920

    def enhanced_screenshot(self, region, screenshot=None):
        """Take a screenshot of a specific region with enhancement"""
        try:
            if screenshot is None:
                screenshot = self.take_screenshot()
            cropped = screenshot.crop(region)

            # Resize for better OCR (same as PC version)
            cropped = cropped.resize((cropped.width * 2, cropped.height * 2), Image.BICUBIC)

            # Convert to grayscale (same as PC version)
            cropped = cropped.convert("L")

            # Enhance contrast (same as PC version)
            enhancer = ImageEnhance.Contrast(cropped)
            enhanced = enhancer.enhance(1.5)

            return enhanced
        except Exception as e:
            log_error(f"Error taking enhanced screenshot: {e}")
            raise

    def enhanced_screenshot_for_failure(self, region, screenshot=None):
        """Enhanced screenshot specifically optimized for white and yellow text on orange background"""
        try:
            if screenshot is None:
                screenshot = self.take_screenshot()
            cropped = screenshot.crop(region)

            # Resize for better OCR
            cropped = cropped.resize((cropped.width * 2, cropped.height * 2), Image.BICUBIC)

            # Convert to RGB to work with color channels
            cropped = cropped.convert("RGB")

            # Convert to numpy for color processing
            img_np = np.array(cropped)

            # Define orange color range (RGB) - for background
            orange_mask = (
                (img_np[:, :, 0] > 150) &  # High red
                (img_np[:, :, 1] > 80) &   # Medium green
                (img_np[:, :, 2] < 100)    # Low blue
            )

            # Define white text range (RGB) - for "Failure" text
            white_mask = (
                (img_np[:, :, 0] > 200) &  # High red
                (img_np[:, :, 1] > 200) &  # High green
                (img_np[:, :, 2] > 200)    # High blue
            )

            # Define yellow text range (RGB) - for failure rate percentages
            yellow_mask = (
                (img_np[:, :, 0] > 190) &  # High red
                (img_np[:, :, 1] > 140) &  # High green
                (img_np[:, :, 2] < 90)     # Low blue
            )

            # Create a new image: black background, white and yellow text
            result = np.zeros_like(img_np)

            # Set white text (for "Failure")
            result[white_mask] = [255, 255, 255]

            # Set yellow text (for percentages) - convert to white for OCR
            result[yellow_mask] = [255, 255, 255]

            # Set orange background to black
            result[orange_mask] = [0, 0, 0]

            # Convert back to PIL
            pil_img = Image.fromarray(result)

            # Convert to grayscale for OCR
            pil_img = pil_img.convert("L")

            # Enhance contrast for better OCR
            pil_img = ImageEnhance.Contrast(pil_img).enhance(1.5)

            return pil_img
        except Exception as e:
            log_error(f"Error taking failure screenshot: {e}")
            raise

    def enhanced_screenshot_for_year(self, region, screenshot=None):
        """Take a screenshot optimized for year detection"""
        try:
            if screenshot is None:
                screenshot = self.take_screenshot()
            cropped = screenshot.crop(region)

            # Enhance for year text detection
            enhancer = ImageEnhance.Contrast(cropped)
            enhanced = enhancer.enhance(2.5)

            enhancer = ImageEnhance.Sharpness(enhanced)
            enhanced = enhancer.enhance(2.0)

            return enhanced
        except Exception as e:
            log_error(f"Error taking year screenshot: {e}")
            raise

    def capture_region(self, region):
        """Capture a specific region of the screen"""
        try:
            screenshot = self.take_screenshot()
            return screenshot.crop(region)
        except Exception as e:
            log_error(f"Error capturing region: {e}")
            raise


# Global instance for backward compatibility
_unified_screenshot = None


def get_unified_screenshot() -> UnifiedScreenshot:
    """Get or create the global unified screenshot instance"""
    global _unified_screenshot
    if _unified_screenshot is None:
        _unified_screenshot = UnifiedScreenshot()
    return _unified_screenshot


def take_screenshot() -> Image.Image:
    """Take screenshot using the configured capture method (backward compatibility)"""
    return get_unified_screenshot().take_screenshot()


def get_screen_size() -> tuple:
    """Get screen size using the configured capture method (backward compatibility)"""
    return get_unified_screenshot().get_screen_size()


def enhanced_screenshot(region, screenshot=None):
    """Take a screenshot of a specific region with enhancement (backward compatibility)"""
    try:
        if screenshot is None:
            screenshot = take_screenshot()
        cropped = screenshot.crop(region)

        # Resize for better OCR (same as PC version)
        cropped = cropped.resize((cropped.width * 2, cropped.height * 2), Image.BICUBIC)

        # Convert to grayscale (same as PC version)
        cropped = cropped.convert("L")

        # Enhance contrast (same as PC version)
        enhancer = ImageEnhance.Contrast(cropped)
        enhanced = enhancer.enhance(1.5)

        return enhanced
    except Exception as e:
        log_error(f"Error taking enhanced screenshot: {e}")
        raise


def enhanced_screenshot_for_failure(region, screenshot=None):
    """Enhanced screenshot specifically optimized for white and yellow text on orange background (backward compatibility)"""
    try:
        if screenshot is None:
            screenshot = take_screenshot()
        cropped = screenshot.crop(region)

        # Resize for better OCR
        cropped = cropped.resize((cropped.width * 2, cropped.height * 2), Image.BICUBIC)

        # Convert to RGB to work with color channels
        cropped = cropped.convert("RGB")

        # Convert to numpy for color processing
        img_np = np.array(cropped)

        # Define orange color range (RGB) - for background
        orange_mask = (
            (img_np[:, :, 0] > 150) &  # High red
            (img_np[:, :, 1] > 80) &   # Medium green
            (img_np[:, :, 2] < 100)    # Low blue
        )

        # Define white text range (RGB) - for "Failure" text
        white_mask = (
            (img_np[:, :, 0] > 200) &  # High red
            (img_np[:, :, 1] > 200) &  # High green
            (img_np[:, :, 2] > 200)    # High blue
        )

        # Define yellow text range (RGB) - for failure rate percentages
        yellow_mask = (
            (img_np[:, :, 0] > 190) &  # High red
            (img_np[:, :, 1] > 140) &  # High green
            (img_np[:, :, 2] < 90)     # Low blue
        )

        # Create a new image: black background, white and yellow text
        result = np.zeros_like(img_np)

        # Set white text (for "Failure")
        result[white_mask] = [255, 255, 255]

        # Set yellow text (for percentages) - convert to white for OCR
        result[yellow_mask] = [255, 255, 255]

        # Set orange background to black
        result[orange_mask] = [0, 0, 0]

        # Convert back to PIL
        pil_img = Image.fromarray(result)

        # Convert to grayscale for OCR
        pil_img = pil_img.convert("L")

        # Enhance contrast for better OCR
        pil_img = ImageEnhance.Contrast(pil_img).enhance(1.5)

        return pil_img
    except Exception as e:
        log_error(f"Error taking failure screenshot: {e}")
        raise


def enhanced_screenshot_for_year(region, screenshot=None):
    """Take a screenshot optimized for year detection (backward compatibility)"""
    try:
        if screenshot is None:
            screenshot = take_screenshot()
        cropped = screenshot.crop(region)

        # Enhance for year text detection
        enhancer = ImageEnhance.Contrast(cropped)
        enhanced = enhancer.enhance(2.5)

        enhancer = ImageEnhance.Sharpness(enhanced)
        enhanced = enhancer.enhance(2.0)

        return enhanced
    except Exception as e:
        log_error(f"Error taking year screenshot: {e}")
        raise


def capture_region(region):
    """Capture a specific region of the screen (backward compatibility)"""
    try:
        screenshot = take_screenshot()
        return screenshot.crop(region)
    except Exception as e:
        log_error(f"Error capturing region: {e}")
        raise
