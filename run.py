import sys
import os

# Add src directory to sys.path so MicMute package can be found
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from MicMute.main import main

if __name__ == '__main__':
    main()
