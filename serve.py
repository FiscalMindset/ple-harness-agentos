"""Entrypoint that serves `harness.solve` over the PLE serve protocol on $PORT."""

import harness
import taskbridge

if __name__ == "__main__":
    taskbridge.run(harness.solve)
