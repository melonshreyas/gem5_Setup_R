def generate(env):
    # macOS stores socket functions inside libSystem
    env.Append(LIBS=['System'])

def exists(env):
    return True
