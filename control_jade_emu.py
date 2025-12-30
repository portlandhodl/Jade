#!/usr/bin/env python3
"""
Script to control the Jade emulator running on port 30121.
Adds a new wallet with the seed phrase "tobacco" repeated 12 times.

NOTE: The emulator must be built with CONFIG_DEBUG_UNATTENDED_CI=y to auto-accept
warnings and user confirmations. This is the default for QEMU builds.
"""

import sys
import logging
import time
import argparse

# Add the jadepy module to the path
sys.path.insert(0, '/home/qrsnap/jade')

from jadepy import JadeAPI

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='Control Jade emulator and set up wallet')
    parser.add_argument('--host', default='localhost', help='Emulator host (default: localhost)')
    parser.add_argument('--port', type=int, default=30121, help='Emulator port (default: 30121)')
    parser.add_argument('--network', default='signet',
                        choices=['mainnet', 'testnet', 'signet', 'localtest', 'liquid', 'testnet-liquid', 'localtest-liquid'],
                        help='Network to use (default: signet)')
    parser.add_argument('--mnemonic', default=None,
                        help='Custom mnemonic (default: "tobacco" repeated 12 times)')
    parser.add_argument('--timeout', type=int, default=30, help='Connection timeout (default: 30)')
    args = parser.parse_args()

    # The seed phrase: "tobacco" repeated 12 times (or custom)
    if args.mnemonic:
        mnemonic = args.mnemonic
    else:
        mnemonic = " ".join(["tobacco"] * 12)

    device = f"tcp:{args.host}:{args.port}"

    logger.info(f"Connecting to Jade emulator at {device}")
    logger.info(f"Using mnemonic: {mnemonic}")
    logger.info(f"Network: {args.network}")

    # Create a JadeAPI instance using TCP connection
    # The device string format is "tcp:host:port"
    jade = JadeAPI.create_serial(device=device, timeout=args.timeout)

    try:
        # Connect to the emulator
        jade.connect()
        logger.info("Connected to Jade emulator")

        # Get version info to verify connection
        version_info = jade.get_version_info()
        logger.info(f"Jade version info:")
        for key, value in version_info.items():
            logger.info(f"  {key}: {value}")

        # Check if this is a debug build (required for set_mnemonic)
        # Debug builds have CONFIG_DEBUG_UNATTENDED_CI which auto-accepts warnings
        jade_state = version_info.get('JADE_STATE', 'UNKNOWN')
        logger.info(f"Jade state: {jade_state}")

        # Set the mnemonic (this is a debug function available in debug builds)
        # This sets the wallet with the given seed phrase
        # The emulator with CONFIG_DEBUG_UNATTENDED_CI=y will auto-accept any warnings
        # Use long_timeout=True since this operation may require user interaction on non-CI builds
        logger.info("Setting mnemonic (debug builds auto-accept warnings)...")

        # Use the internal _jadeRpc method with long_timeout=True to wait indefinitely
        # for user confirmation if needed
        params = {'mnemonic': mnemonic, 'passphrase': None, 'temporary_wallet': False}
        result = jade._jadeRpc('debug_set_mnemonic', params, long_timeout=True)

        if result:
            logger.info("Successfully set wallet with mnemonic!")
            logger.info(f"Mnemonic: {mnemonic}")

            # Get an xpub to verify the wallet is working
            logger.info(f"Getting xpub for network '{args.network}'...")
            try:
                # Get root xpub
                xpub = jade.get_xpub(args.network, [])
                logger.info(f"Root xpub: {xpub}")

                # Get a derived xpub (BIP84 for signet/testnet)
                if args.network in ['signet', 'testnet', 'localtest']:
                    # BIP84 path for testnet: m/84'/1'/0'
                    derived_path = [2147483732, 2147483649, 2147483648]  # 84', 1', 0'
                elif args.network == 'mainnet':
                    # BIP84 path for mainnet: m/84'/0'/0'
                    derived_path = [2147483732, 2147483648, 2147483648]  # 84', 0', 0'
                else:
                    derived_path = [2147483648]  # 0'

                derived_xpub = jade.get_xpub(args.network, derived_path)
                logger.info(f"Derived xpub (path {derived_path}): {derived_xpub}")

            except Exception as e:
                logger.warning(f"Could not get xpub: {e}")
        else:
            logger.error("Failed to set mnemonic")
            return 1

    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # Disconnect from the emulator
        jade.disconnect()
        logger.info("Disconnected from Jade emulator")

    return 0


if __name__ == "__main__":
    sys.exit(main())
