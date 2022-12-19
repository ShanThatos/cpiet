import pickle
import os.path

OPS = [
    ("decrement", lambda x: x - 1, ["push", "subtract"]),
    ("increment", lambda x: x + 1, ["push", "add"]),
    ("square", lambda x: x * x, ["duplicate", "multiply"]),
    ("cube", lambda x: x * x * x, ["duplicate", "duplicate", "multiply", "multiply"]),
    ("double", lambda x: x * 2, ["duplicate", "add"]),
]
DUO_OPS = [
    ("add", lambda x, y: x + y, ["add"]),
    ("subtract", lambda x, y: x - y, ["subtract"]),
    ("multiply", lambda x, y: x * y, ["multiply"]),
]

nums = {
    0: (["push", "not"], []),
    1: (["push"], [])
}

MAX_M = 1000
M = range(1, MAX_M + 1)

results = 0
while True:
    for i in M:
        cmds, actions = nums[i]
        for action, op, cmd in OPS:
            n = op(i)
            if n > 1 and (n not in nums or len(nums[n][0]) >= len(cmds) + len(cmd)):
                nums[n] = (cmds + cmd, actions + [action])
        
        for j in range(1, i):
            j_cmds, j_actions = nums[j]
            for action, op, cmd in DUO_OPS:
                n = op(i, j)
                if n > 1 and (n not in nums or len(nums[n][0]) >= len(cmds) + len(j_cmds) + len(cmd)):
                    nums[n] = (cmds + j_cmds + cmd, actions + ["combine"] + j_actions + [action])

    new_results = sum(len(nums[i][0]) for i in M)
    if new_results == results:
        break
    results = new_results

# for i in M:
#     print(i, nums[i][0])

print(results)

nums = [nums[i][0] for i in range(MAX_M)]
numgen_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "numgen.pickle")
pickle.dump(nums, open(numgen_path, "wb"), pickle.HIGHEST_PROTOCOL)
