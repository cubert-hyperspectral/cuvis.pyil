
try:
    import numpy as np
    print(np.get_include())
except ImportError:
    print('no numpy')
