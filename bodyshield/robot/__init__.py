"""Hardware entry points.

These modules are intentionally safety-gated and do not issue raw motor
commands.  They exist so the non-hardware stack can be imported and tested
without accidentally entering the hardware phase.
"""
