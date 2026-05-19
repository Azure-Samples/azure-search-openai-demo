import json
import os
import random
import sys

SAVE_FILE = "casino_save.json"

# ---------- Player ----------

class Player:
    def __init__(self, name: str, balance: int = 500, xp: int = 0):
        self.name = name
        self.balance = balance
        self.xp = xp
        self.games_stats = {
            "slots": {"played": 0, "won": 0},
            "blackjack": {"played": 0, "won": 0},
            "roulette": {"played": 0, "won": 0},
            "keno": {"played": 0, "won": 0},
            "crash": {"played": 0, "won": 0},
            "plinko": {"played": 0, "won": 0},
        }

    @property
    def level(self) -> int:
        return self.xp // 100 + 1

    def add_balance(self, amount: int | float):
        self.balance = max(self.balance + amount, 0)

    def add_xp(self, amount: int):
        self.xp += max(amount, 0)

    def record_game(self, game: str, won: bool):
        """Record game result for statistics."""
        if game in self.games_stats:
            self.games_stats[game]["played"] += 1
            if won:
                self.games_stats[game]["won"] += 1


# ---------- Save / Load ----------

def save_profile(player: Player):
    data = {
        "name": player.name,
        "balance": player.balance,
        "xp": player.xp,
        "games_stats": player.games_stats,
    }
    with open(SAVE_FILE, "w") as f:
        json.dump(data, f, indent=2)
    print("💾 Game saved.")


def load_profile() -> Player | None:
    if not os.path.exists(SAVE_FILE):
        return None
    try:
        with open(SAVE_FILE, "r") as f:
            data = json.load(f)
        player = Player(
            name=data.get("name", "Guest"),
            balance=data.get("balance", 500),
            xp=data.get("xp", 0),
        )
        player.games_stats = data.get("games_stats", player.games_stats)
        return player
    except Exception:
        return None


# ---------- Helpers ----------

def ask_int(prompt: str, min_val: int = 0, max_val: int | None = None) -> int:
    """Get integer input with validation."""
    while True:
        try:
            val = int(input(prompt))
            if val < min_val:
                print(f"❌ Value must be >= {min_val}")
                continue
            if max_val is not None and val > max_val:
                print(f"❌ Value must be <= {max_val}")
                continue
            return val
        except ValueError:
            print("❌ Enter a valid integer.")


def ask_choice(prompt: str, valid_choices: list[str]) -> str:
    """Get choice input with validation and retry."""
    while True:
        choice = input(prompt).strip().lower()
        if choice in valid_choices:
            return choice
        print(f"❌ Invalid choice. Valid options: {', '.join(valid_choices)}")


def press_enter():
    """Pause and wait for user to continue."""
    input("\n⏸️ Press Enter to continue...")


def show_statistics(player: Player):
    """Display player's game statistics."""
    print("\n=== 📊 Game Statistics ===")
    print(f"Player: {player.name} | Level: {player.level} | Total XP: {player.xp}")
    print(f"Balance: ${player.balance}\n")
    
    print("Game Statistics:")
    print("-" * 50)
    
    total_played = 0
    total_won = 0
    
    for game, stats in sorted(player.games_stats.items()):
        played = stats["played"]
        won = stats["won"]
        total_played += played
        total_won += won
        
        if played > 0:
            win_rate = (won / played) * 100
            print(f"{game.capitalize():12} | Played: {played:3} | Won: {won:3} | Win Rate: {win_rate:5.1f}%")
        else:
            print(f"{game.capitalize():12} | Not played yet")
    
    print("-" * 50)
    if total_played > 0:
        overall_rate = (total_won / total_played) * 100
        print(f"{'OVERALL':12} | Played: {total_played:3} | Won: {total_won:3} | Win Rate: {overall_rate:5.1f}%")
    else:
        print("No games played yet!")
    
    press_enter()


# ---------- Slots ----------

SYMBOLS = ["🍒", "🍋", "🍊", "🍇", "⭐", "💎", "7"]
PAYOUTS = {
    "🍒": 2,
    "🍋": 3,
    "🍊": 4,
    "🍇": 5,
    "⭐": 10,
    "💎": 20,
    "7": 50,
}

def play_slots(player: Player):
    print("\n=== 🎰 Slot Machine ===")
    print(f"Balance: ${player.balance}")
    bet = ask_int("Bet amount (0 to cancel): ", 0, player.balance)
    if bet == 0:
        return

    player.add_balance(-bet)
    player.add_xp(5)

    reels = [random.choice(SYMBOLS) for _ in range(3)]
    print("Spinning...")
    print(" | ".join(reels))

    r1, r2, r3 = reels
    won = False
    
    if r1 == r2 == r3:
        win = bet * PAYOUTS[r1]
        player.add_balance(win)
        player.add_xp(20)
        print(f"🎉 JACKPOT! You won ${win}!")
        won = True
    elif r1 == r2 or r2 == r3 or r1 == r3:
        win = int(bet * 1.5)
        player.add_balance(win)
        player.add_xp(10)
        print(f"✨ Nice! You won ${win}.")
        won = True
    else:
        print("❌ No win this time.")

    player.record_game("slots", won)
    print(f"New balance: ${player.balance}")
    press_enter()


# ---------- Blackjack ----------

SUITS = ["♠", "♥", "♦", "♣"]
RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]

def create_deck():
    """Create a standard deck of cards."""
    return [(r, s) for s in SUITS for r in RANKS]

def hand_value(hand):
    """Calculate blackjack hand value with Ace handling."""
    total = 0
    aces = 0
    for rank, _ in hand:
        if rank == "A":
            total += 11
            aces += 1
        elif rank in ["J", "Q", "K"]:
            total += 10
        else:
            total += int(rank)
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    return total

def is_blackjack(hand):
    """Check if hand is a natural blackjack."""
    return len(hand) == 2 and hand_value(hand) == 21

def show_hand(label, hand, hide_second=False):
    """Display a hand of cards."""
    if hide_second and len(hand) > 1:
        shown = [f"{hand[0][0]}{hand[0][1]}", "??"]
    else:
        shown = [f"{r}{s}" for r, s in hand]
    print(f"{label}: {' '.join(shown)} (value: {'?' if hide_second else hand_value(hand)})")

def play_blackjack(player: Player):
    print("\n=== 🃏 Blackjack ===")
    print(f"Balance: ${player.balance}")
    bet = ask_int("Bet amount (0 to cancel): ", 0, player.balance)
    if bet == 0:
        return

    player.add_balance(-bet)
    player.add_xp(5)

    deck = create_deck()
    random.shuffle(deck)

    player_hand = [deck.pop(), deck.pop()]
    dealer_hand = [deck.pop(), deck.pop()]

    # Handle natural blackjacks
    if is_blackjack(player_hand) or is_blackjack(dealer_hand):
        show_hand("Dealer", dealer_hand)
        show_hand("Player", player_hand)
        won = False
        
        if is_blackjack(player_hand) and is_blackjack(dealer_hand):
            print("Both have blackjack. Push.")
            player.add_balance(bet)
        elif is_blackjack(player_hand):
            win = int(bet * 1.5)
            player.add_balance(bet + win)
            player.add_xp(25)
            print(f"🎉 Blackjack! You win ${win}.")
            won = True
        else:
            print("❌ Dealer has blackjack. You lose.")
        
        player.record_game("blackjack", won)
        print(f"New balance: ${player.balance}")
        press_enter()
        return

    # Player's turn
    while True:
        show_hand("Dealer", dealer_hand, hide_second=True)
        show_hand("Player", player_hand)
        
        if hand_value(player_hand) > 21:
            print("❌ You bust. Dealer wins.")
            player.record_game("blackjack", False)
            print(f"New balance: ${player.balance}")
            press_enter()
            return
        
        choice = ask_choice("(H)it, (S)tand: ", ["h", "s"])
        if choice == "h":
            # Reshuffle if deck is low
            if len(deck) < 5:
                deck = create_deck()
                random.shuffle(deck)
            player_hand.append(deck.pop())
        elif choice == "s":
            break

    # Dealer's turn
    while hand_value(dealer_hand) < 17:
        if len(deck) < 5:
            deck = create_deck()
            random.shuffle(deck)
        dealer_hand.append(deck.pop())

    show_hand("Dealer", dealer_hand)
    show_hand("Player", player_hand)

    p_val = hand_value(player_hand)
    d_val = hand_value(dealer_hand)
    won = False

    if d_val > 21 or p_val > d_val:
        player.add_balance(bet * 2)
        player.add_xp(15)
        print(f"✨ You win ${bet}.")
        won = True
    elif p_val < d_val:
        print("❌ Dealer wins.")
    else:
        player.add_balance(bet)
        print("Push.")

    player.record_game("blackjack", won)
    print(f"New balance: ${player.balance}")
    press_enter()


# ---------- Roulette (red/black) ----------

def play_roulette(player: Player):
    print("\n=== 🎡 Roulette (Red/Black) ===")
    print(f"Balance: ${player.balance}")
    bet = ask_int("Bet amount (0 to cancel): ", 0, player.balance)
    if bet == 0:
        return

    # Validate choice BEFORE deducting resources
    color_choice = ask_choice("Bet on (r)ed or (b)lack: ", ["r", "b"])

    player.add_balance(-bet)
    player.add_xp(5)

    number = random.randint(0, 36)
    if number == 0:
        color = "g"
    elif number % 2 == 0:
        color = "r"
    else:
        color = "b"

    color_name = "red" if color == "r" else "black" if color == "b" else "green"
    print(f"Spin result: {number} ({color_name})")

    won = False
    if color == "g":
        print("🏠 House wins (green).")
    elif color == color_choice:
        win = bet * 2
        player.add_balance(win)
        player.add_xp(10)
        print(f"✨ You win ${win}.")
        won = True
    else:
        print("❌ You lose.")

    player.record_game("roulette", won)
    print(f"New balance: ${player.balance}")
    press_enter()


# ---------- Keno ----------

def play_keno(player: Player):
    print("\n=== 🔢 Keno ===")
    print(f"Balance: ${player.balance}")
    bet = ask_int("Bet amount (0 to cancel): ", 0, player.balance)
    if bet == 0:
        return

    # Validate picks BEFORE deducting resources
    picks = []
    while not picks:
        print("Pick up to 10 numbers between 1 and 40 (comma separated):")
        raw = input("> ").strip()
        try:
            picks = sorted(set(int(x.strip()) for x in raw.split(",") if x.strip()))
        except ValueError:
            print("❌ Invalid input. Enter numbers separated by commas.")
            continue
        
        picks = [p for p in picks if 1 <= p <= 40][:10]
        if not picks:
            print("❌ No valid picks. Please enter numbers between 1 and 40.")

    player.add_balance(-bet)
    player.add_xp(5)

    pool = list(range(1, 41))
    random.shuffle(pool)
    drawn = sorted(pool[:10])

    print(f"Your picks: {picks}")
    print(f"Drawn:      {drawn}")

    won = False
    hits = len(set(picks) & set(drawn))
    if hits == 0:
        print("❌ No hits. Better luck next time.")
    else:
        payout = bet * hits
        player.add_balance(payout)
        player.add_xp(hits * 5)
        print(f"✨ You hit {hits} number(s) and won ${payout}.")
        won = True

    player.record_game("keno", won)
    print(f"New balance: ${player.balance}")
    press_enter()


# ---------- Crash ----------

def play_crash(player: Player):
    print("\n=== 📈 Crash ===")
    print(f"Balance: ${player.balance}")
    bet = ask_int("Bet amount (0 to cancel): ", 0, player.balance)
    if bet == 0:
        return

    player.add_balance(-bet)
    player.add_xp(5)

    r = random.random()
    bust = round(1 + (r ** -1.5), 2)
    multiplier = 1.0
    cashed_out = False

    print("Game started. Type 'c' to cash out before it crashes.")
    while True:
        print(f"Multiplier: {multiplier:.2f}x", end="  ")
        if multiplier >= bust:
            print(f"\n💥 Crashed at {bust}x!")
            break
        
        choice = ask_choice("(c to cash, Enter to continue): ", ["c", ""])
        if choice == "c":
            win = round(bet * multiplier, 2)
            player.add_balance(win)
            player.add_xp(10)
            print(f"✨ You cashed out at {multiplier:.2f}x and won ${win}.")
            cashed_out = True
            break
        multiplier = round(multiplier + multiplier * 0.1, 2)

    won = cashed_out
    if not cashed_out:
        print("❌ You lost this round.")

    player.record_game("crash", won)
    print(f"New balance: ${player.balance}")
    press_enter()


# ---------- Plinko ----------

PLINKO_SLOTS = [-50, -20, 0, 10, 20, 50]

def play_plinko(player: Player):
    print("\n=== 🟣 Plinko ===")
    print(f"Balance: ${player.balance}")
    bet = ask_int("Bet amount (0 to cancel): ", 0, player.balance)
    if bet == 0:
        return

    player.add_balance(-bet)
    player.add_xp(5)

    print("Dropping ball...")
    idx = random.randint(0, len(PLINKO_SLOTS) - 1)
    modifier = PLINKO_SLOTS[idx]
    win = bet + modifier

    print("Slots:", PLINKO_SLOTS)
    print(f"Landed on: {modifier}")

    won = False
    if win > 0:
        player.add_balance(win)
        player.add_xp(10)
        print(f"✨ You won ${win}!")
        won = True
    else:
        print(f"❌ You lost ${-win}.")

    player.record_game("plinko", won)
    print(f"New balance: ${player.balance}")
    press_enter()


# ---------- Main loop ----------

def main():
    print("=== 🎰 High Roller CLI Casino ===\n")

    saved = load_profile()
    if saved:
        print(f"✅ Loaded profile for {saved.name}.")
        player = saved
    else:
        name = input("Enter your name: ").strip() or "Guest"
        player = Player(name)

    while True:
        print("\n" + "=" * 50)
        print(f"Player: {player.name} | Balance: ${player.balance} | XP: {player.xp} | Level: {player.level}")
        print("=" * 50)
        print("1) 🎰 Slot Machine")
        print("2) 🃏 Blackjack")
        print("3) 🎡 Roulette")
        print("4) 🔢 Keno")
        print("5) 📈 Crash")
        print("6) 🟣 Plinko")
        print("7) 📊 Statistics")
        print("8) 💾 Save Game")
        print("0) 🚪 Quit")
        print("=" * 50)
        
        choice = input("Choose a game: ").strip()

        if choice == "1":
            play_slots(player)
        elif choice == "2":
            play_blackjack(player)
        elif choice == "3":
            play_roulette(player)
        elif choice == "4":
            play_keno(player)
        elif choice == "5":
            play_crash(player)
        elif choice == "6":
            play_plinko(player)
        elif choice == "7":
            show_statistics(player)
        elif choice == "8":
            save_profile(player)
        elif choice == "0":
            save_profile(player)
            print("🎉 Thanks for playing!")
            sys.exit(0)
        else:
            print("❌ Invalid choice.")

if __name__ == "__main__":
    main()
