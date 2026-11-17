"""Reuse TASK05 handoff operations with TASK06's NEW current-code freeze."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'task05'))
import handoff
handoff.FROZEN=Path(__file__).resolve().parent/'ordinary-current-v1'
if __name__=='__main__':handoff.main()
