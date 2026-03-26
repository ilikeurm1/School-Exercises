ph = [6.8, 7.1, 7.4, 6.9, 7.0, 7.2, 6.6]

avg = sum(ph) / len(ph)

print(f"Average pH: {avg:.5}")

print("The solution is: ", end="")

if avg > 7:
    print("Basic")
elif avg == 7:
    print("Neutral")
else:
    print("Acidic")
