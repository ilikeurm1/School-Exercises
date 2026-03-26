temps = [18.5, 21, 19.8, 20, 22.3, 17.6]

over = 0
under = 0
twenty = 0

for temp in temps:
    if temp == 20:
        twenty += 1
    elif temp < 20:
        under += 1
    else:
        over += 1

print(f"Over 20: {over}")
print(f"20: {twenty}")
print(f"Under: {under}")
