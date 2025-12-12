# Puzzle 135 Randomized Kangaroo Solver
# Based on concept by Pollard & fe57
import time, os, sys, random
from gmpy2 import mpz, powmod, invert, jacobi
from math import log

# -----------------------------------------------------------------------------
# 1. SETUP & UTILS
# -----------------------------------------------------------------------------
os.system("cls||clear")

# Secp256k1 Constants
modulo = mpz(0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F)
Gx = mpz(0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798)
Gy = mpz(0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8)
PG = (Gx, Gy)

def add(P, Q):
    if P == (0, 0): return Q
    if Q == (0, 0): return P
    Px, Py = P
    Qx, Qy = Q
    
    if Px == Qx:
        if Py == Qy:
            inv_2Py = invert((Py << 1) % modulo, modulo)
            m = (3 * Px * Px * inv_2Py) % modulo
        else:
            return (0, 0)
    else:
        inv_diff_x = invert(Qx - Px, modulo)
        m = ((Qy - Py) * inv_diff_x) % modulo
        
    x = (m * m - Px - Qx) % modulo
    y = (m * (Px - x) - Py) % modulo
    return (x, y)

def mul(k, P=PG):
    R0, R1 = (0, 0), P
    for i in reversed(range(k.bit_length())):
        if (k >> i) & 1:
            R0, R1 = add(R0, R1), add(R1, R1)
        else:
            R1, R0 = add(R0, R1), add(R0, R0)
    return R0

def X2Y(X, y_parity, p=modulo):
    X = mpz(X)
    X3_7 = (pow(X, 3, p) + 7) % p
    if jacobi(X3_7, p) != 1: return None
    Y = powmod(X3_7, (p + 1) >> 2, p)
    return Y if (Y & 1) == y_parity else (p - Y)

def handle_solution(solution):
    HEX = f"{abs(solution):064x}"
    dec = int(HEX, 16)
    print(f"\n\n\033[32m" + "█"*60)
    print(f"██ [!!!] PUZZLE 135 SOLVED [!!!]")
    print(f"██ Private Key (Decimal): {dec}")
    print(f"██ Private Key (HEX)    : {HEX}")
    print(f"██ Target Address       : 16RGFo6hjq9ym6Pj7N5H7L1NR1rVPJyw2v")
    print("█"*60 + "\033[0m")
    with open("PUZZLE_135_FOUND.txt", "a") as file:
        file.write(f"SOLVED: {HEX}\nDecimal: {dec}\n")
    sys.exit(0)

# -----------------------------------------------------------------------------
# 2. CONFIGURATION (PUZZLE 135)
# -----------------------------------------------------------------------------
puzzle_bit = 135
# Range: 2^134 to 2^135 - 1
start_range = mpz(1) << 134
end_range   = (mpz(1) << 135) - 1
range_len   = end_range - start_range

# Target Public Key (Puzzle 135)
target_pub_hex = "02145d2611c823a396ef6712ce0f712f09b9b4f3135e3e0aa3230fb9b6d08d1e16"

# Kangaroo Settings
kangaroo_power = 8   # 256 Kangaroos
Nt = Nw = 1 << kangaroo_power
DP_rarity = 1 << 14  # Adjust for memory/collision frequency
hop_modulo = 50      # Power of 2 jumps
powers_of_two = [mpz(1) << pw for pw in range(hop_modulo)]

# Pre-compute Jump Table
sys.stdout.write(f"\033[01;33m[+] Configuring for Puzzle {puzzle_bit}...\033[0m\n")
P_Table = [PG]
for _ in range(hop_modulo):
    P_Table.append(mul(2, P_Table[-1]))

# Parse Target
target_x = mpz(int(target_pub_hex[2:66], 16))
target_parity = int(target_pub_hex[:2]) - 2
target_y = X2Y(target_x, target_parity)
if target_y is None:
    print("[ERROR] Invalid Public Key!")
    sys.exit(1)
W0 = (target_x, target_y)

# Limits
MAX_HOPS_PER_ROUND = 5_000_000  # تعداد پرش قبل از تغییر مکان شانسی

# -----------------------------------------------------------------------------
# 3. MAIN LOOP
# -----------------------------------------------------------------------------
def run_random_kangaroo():
    round_num = 1
    
    print(f"\033[01;36m[+] Target Address: 16RGFo6hjq9ym6Pj7N5H7L1NR1rVPJyw2v")
    print(f"[+] Range Start   : {hex(start_range)}")
    print(f"[+] Search Space  : 2^{puzzle_bit}")
    print(f"[+] Mode          : Random Jump + Local Kangaroo Scan")
    print(f"[+] Restart Limit : {MAX_HOPS_PER_ROUND:,} hops per round\033[0m\n")

    while True:
        # --- PHASE 1: JUMP TO RANDOM LOCATION ---
        # انتخاب یک نقطه تصادفی در محدوده عظیم 2^135
        # این همان بخش "شانس" است
        rnd = random.SystemRandom().randint(0, int(range_len))
        base_tame_start = start_range + mpz(rnd)
        
        t_abs = []
        T = []
        
        # ساخت گله Tame در اطراف نقطه تصادفی
        for _ in range(Nt):
            # کمی پراکندگی محلی برای گله
            local_offset = random.randint(0, 1 << 40) 
            val = base_tame_start + local_offset
            t_abs.append(val)
            T.append(mul(val)) # محاسبه سنگین نقطه شروع

        # ساخت گله Wild از تارگت
        w = [random.randint(1, 1 << 40) for _ in range(Nw)]
        W = [add(W0, mul(wk)) for wk in w]
        
        tame_dps = {}
        wild_dps = {}
        
        hops = 0
        t0 = time.time()
        start_time = t0
        
        sys.stdout.write(f"\r\033[01;33m[Round {round_num}] Jumping to random segment {hex(base_tame_start)[:15]}... \033[0m")
        sys.stdout.flush()

        # --- PHASE 2: SCAN (HOPPING) ---
        while hops < MAX_HOPS_PER_ROUND:
            # Tame Step
            for k in range(Nt):
                Tk_x = T[k][0]
                pw = int(Tk_x % hop_modulo)
                dt = powers_of_two[pw]
                
                if Tk_x % DP_rarity == 0:
                    if Tk_x in wild_dps:
                        # FOUND!
                        pk = t_abs[k] - wild_dps[Tk_x]
                        handle_solution(pk)
                    tame_dps[Tk_x] = t_abs[k]
                
                t_abs[k] += dt
                T[k] = add(P_Table[pw], T[k])
                hops += 1

            # Wild Step
            for k in range(Nw):
                Wk_x = W[k][0]
                pw = int(Wk_x % hop_modulo)
                dw = powers_of_two[pw]
                
                if Wk_x % DP_rarity == 0:
                    if Wk_x in tame_dps:
                        # FOUND!
                        pk = tame_dps[Wk_x] - w[k]
                        handle_solution(pk)
                    wild_dps[Wk_x] = w[k]
                
                w[k] += dw
                W[k] = add(P_Table[pw], W[k])
                hops += 1
            
            # Status Update
            if hops % 5000 == 0:
                elapsed = time.time() - start_time
                spd = hops / (elapsed + 0.001)
                sys.stdout.write(f"\r[Round {round_num}] Hops: {hops/1000:.0f}k/{MAX_HOPS_PER_ROUND/1000:.0f}k | Speed: {spd/1000:.1f} kH/s | DPs: {len(tame_dps)+len(wild_dps)}   ")
                sys.stdout.flush()

        # Restarting
        round_num += 1

if __name__ == "__main__":
    try:
        run_random_kangaroo()
    except KeyboardInterrupt:
        print("\n[!] Stopped.")
