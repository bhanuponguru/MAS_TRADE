import os

# The problems here are small; multi-threaded BLAS only adds overhead (a 5x slowdown on the market simulations).
for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(var, "1")
