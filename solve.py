# solve.py
import ast, operator, sys

def solve(nums):
    """找到任意一个解，返回表达式字符串"""
    target = 24
    def dfs(arr):
        if len(arr) == 1:
            if abs(arr[0][0] - target) < 1e-6:
                return arr[0][1]
            return None
        for i in range(len(arr)):
            for j in range(len(arr)):
                if i == j:
                    continue
                rest = [arr[k] for k in range(len(arr)) if k != i and k != j]
                (va, ea), (vb, eb) = arr[i], arr[j]
                candidates = [
                    (va + vb, f"({ea}+{eb})"),
                    (va - vb, f"({ea}-{eb})"),
                    (vb - va, f"({eb}-{ea})"),
                    (va * vb, f"({ea}*{eb})"),
                ]
                if abs(vb) > 1e-9:
                    candidates.append((va / vb, f"({ea}/{eb})"))
                if abs(va) > 1e-9:
                    candidates.append((vb / va, f"({eb}/{ea})"))
                for val, expr in candidates:
                    r = dfs(rest + [(val, expr)])
                    if r:
                        return r
        return None
    return dfs([(n, str(n)) for n in nums])

if __name__ == "__main__":
    nums = [int(x) for x in sys.argv[1:]]
    print(solve(nums))
