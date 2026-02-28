# Dump global-metadata.dat from memory

import pymem
import pymem.process
import pymem.pattern
import os
import sys

class MetadataDumper:
    def __init__(self, process_name: str, target_size_bytes: int):
        self.process_name = process_name
        # Read original size + 1MB to prevent overflow
        self.dump_size = target_size_bytes + (1 * 1024 * 1024) 
        self.pm = None

    def attach(self):
        try:
            self.pm = pymem.Pymem(self.process_name)
            print(f"[+] Successfully attached to process: {self.process_name} (PID: {self.pm.process_id})")
        except Exception as e:
            print(f"[-] Cannot find or attach to process '{self.process_name}'. Please ensure the game is running.")
            sys.exit(1)

    def scan_and_dump_all(self):
        print("[*] Starting to scan memory for *all* global-metadata signatures...")
        
        # Signature: magic number
        signature = b'\xAF\x1B\xB1\xFA'
        
        try:
            # Key modification: return_multiple=True, find all matches
            results = pymem.pattern.pattern_scan_all(self.pm.process_handle, signature, return_multiple=True)
            
            if not results:
                print("[-] No signature found in memory. Header might be erased or encryption method changed.")
                return

            print(f"[!] Found {len(results)} potential addresses. Starting extraction...")

            for index, address in enumerate(results):
                print(f"\n--- Processing address {index + 1}: {hex(address)} ---")
                self.dump_to_file(address, index)

        except Exception as e:
            print(f"[-] Error during scanning: {e}")

    def dump_to_file(self, address, index):
        try:
            # Try direct read
            data = self.pm.read_bytes(address, self.dump_size)
            self._save(data, index, address)
            
        except pymem.exception.MemoryReadError:
            print(f"[-] Address {hex(address)} read failed (Error 299), trying safe read...")
            self._safe_dump(address, index)
        except Exception as e:
            print(f"[-] Unknown error: {e}")

    def _safe_dump(self, start_address, index):
        buffer = bytearray()
        chunk_size = 1024 
        current_addr = start_address
        bytes_read = 0
        
        while bytes_read < self.dump_size:
            try:
                chunk = self.pm.read_bytes(current_addr, chunk_size)
                buffer.extend(chunk)
                current_addr += chunk_size
                bytes_read += chunk_size
            except Exception:
                break
        
        if len(buffer) > 1024 * 1024: 
            self._save(buffer, index, start_address)
        else:
            print("[-] Data too small, skipping save.")

    def _save(self, data, index, address):
        # Filename includes address for identification
        filename = f"dump_{index}_{hex(address)}.dat"
        with open(filename, "wb") as f:
            f.write(data)
        print(f"[+] Saved: {filename} (size: {len(data)} bytes)")
        self._check_if_decrypted(data)

    def _check_if_decrypted(self, data):
        """
        Simple heuristic check: look for common plaintext strings
        """
        # Check if data contains "UnityEngine" or "System" - common class names
        # Decrypted Metadata should show many plaintext class names
        sample = data[:1024 * 1024] # Only check first 1MB
        if b'UnityEngine' in sample or b'm_scor' in sample or b'System.String' in sample:
            print(f"    [*] Hint: This file looks like decrypted! (Found plaintext strings)")
        else:
            print(f"    [!] Hint: This file still appears to be encrypted/garbled.")

if __name__ == "__main__":
    TARGET_PROCESS = "GrilsFrontLine.exe" 
    # Your original file size
    ORIGINAL_FILE_SIZE = 32880320 
    
    dumper = MetadataDumper(TARGET_PROCESS, ORIGINAL_FILE_SIZE)
    dumper.attach()
    dumper.scan_and_dump_all()