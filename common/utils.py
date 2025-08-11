"""
    Simple utils functions
"""
import inspect

def getdict(struct):
    result = {}
    #print struct
    def get_value(value):
        if (type(value) not in [int, float, bool, bytes]) and not bool(value):
            # it's a null pointer
            value = None
        elif (type(value) is bytes):
            # Special "byte" character : use decode to remove b'xx' notation
            value = value.decode()
        elif hasattr(value, "_length_") and hasattr(value, "_type_"):
            # Probably an array
            #print value
            value = get_array(value)
        elif hasattr(value, "_fields_"):
            # Probably another struct
            value = getdict(value)
        return value
    def get_array(array):
        ar = []
        for value in array:
            value = get_value(value)
            ar.append(value)
        return ar
    for f  in struct._fields_:
        field = f[0]
        value = getattr(struct, field)
        # if the type is not a primitive and it evaluates to False ...
        value = get_value(value)
        result[field] = value
    return result

def wrap_function(lib, funcname, restype, argtypes):
    """Simplify wrapping ctypes functions"""
    func = lib.__getattr__(funcname)
    func.restype = restype
    func.argtypes = argtypes
    return func

def current_method_name():
    # [0] is this method's frame, [1] is the parent's frame - which we want
    return inspect.stack()[1].function
