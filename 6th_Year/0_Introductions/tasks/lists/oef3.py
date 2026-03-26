pows = [-5, 12, -3, 8, 0, -2, 15]

print("Negative: [", *([n for n in pows if n > 0]), "]")
print("Positive: [", *([n for n in pows if n < 0]), "]")
print("Zeros (idx, 0): [", *([f"({i}, {n})" for i, n in enumerate(pows) if n == 0]), "]")
