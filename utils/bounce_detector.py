class BounceDetector:
    def __init__(self):
        self.afterbuy = None

    def detect_bounce(self, current_price, up_bounce_threshold=1.1, down_bounce_threshold=0.9):
        """
        Detects meaningful bounces after the first buy.

        Args:
            current_price: Current price to evaluate
            up_bounce_threshold: Multiplier for upward bounce (1.1 = +10%)
            down_bounce_threshold: Multiplier for downward bounce (0.9 = -10%)

        Returns:
            dict: Current bounce state including bounce_list
        """
        # === Initialize on first call ===
        if self.afterbuy is None:
            self.afterbuy = {
                "min": current_price,
                "max": current_price,
                "extreme": current_price,  # Last extreme point (top or bottom)
                "bounce_list": [],
                "direction": None,  # "up" or "down"
            }

        ab = self.afterbuy

        # === Update min/max trackers ===
        ab["min"] = min(ab["min"], current_price)
        ab["max"] = max(ab["max"], current_price)

        # === Initialize direction on first move ===
        if ab["direction"] is None:
            if current_price > ab["extreme"]:
                ab["direction"] = "up"
            elif current_price < ab["extreme"]:
                ab["direction"] = "down"
            ab["extreme"] = current_price
            return ab

        # === Track in current direction ===
        if ab["direction"] == "up":
            # Update top if price goes higher
            if current_price > ab["extreme"]:
                ab["extreme"] = current_price

            # Check for downward bounce (price drops by threshold from top)
            elif current_price / ab["extreme"] <= down_bounce_threshold:
                # Record the completed UP bounce
                prev_bottom = ab["bounce_list"][-1]["end"] if ab["bounce_list"] else ab["min"]
                ab["bounce_list"].append({
                    "type": "up",
                    "start": prev_bottom,
                    "end": ab["extreme"],
                    "gain": ab["extreme"] / prev_bottom - 1.0,
                })
                # Switch to down direction
                ab["direction"] = "down"
                ab["extreme"] = current_price

        elif ab["direction"] == "down":
            # Update bottom if price goes lower
            if current_price < ab["extreme"]:
                ab["extreme"] = current_price

            # Check for upward bounce (price rises by threshold from bottom)
            elif current_price / ab["extreme"] >= up_bounce_threshold:
                # Record the completed DOWN bounce
                prev_top = ab["bounce_list"][-1]["end"] if ab["bounce_list"] else ab["max"]
                ab["bounce_list"].append({
                    "type": "down",
                    "start": prev_top,
                    "end": ab["extreme"],
                    "gain": ab["extreme"] / prev_top - 1.0,
                })
                # Switch to up direction
                ab["direction"] = "up"
                ab["extreme"] = current_price

        return ab

    def reset(self):
        """Reset the detector state"""
        self.afterbuy = None


# ==================== TESTS ====================

def test_simple_up_bounce():
    """Test: Price goes down then bounces up 10%"""
    print("\n=== TEST 1: Simple Up Bounce ===")
    detector = BounceDetector()

    prices = [100, 95, 90, 85, 80, 88, 96, 105]  # Down to 80, then up to 105
    print(f"Price sequence: {prices}")

    for price in prices:
        state = detector.detect_bounce(price, up_bounce_threshold=1.1, down_bounce_threshold=0.9)
        direction = state['direction'] if state['direction'] else 'None'
        print(f"Price: {price:6.2f} | Direction: {direction:>5} | "
              f"Extreme: {state['extreme']:6.2f} | Bounces: {len(state['bounce_list'])}")

    print(f"\nFinal bounces detected: {len(state['bounce_list'])}")
    for i, bounce in enumerate(state['bounce_list']):
        print(f"  Bounce {i+1}: {bounce['type']:>4} | "
              f"{bounce['start']:6.2f} → {bounce['end']:6.2f} | "
              f"Gain: {bounce['gain']*100:+6.1f}%")


def test_multiple_bounces():
    """Test: Multiple up and down bounces"""
    print("\n=== TEST 2: Multiple Bounces ===")
    detector = BounceDetector()

    # Clear pattern: 100 -> 80, 80 -> 100, 100 -> 70, 70 -> 100, 100 -> 80, 80 -> 100, 100 -> 90
    prices = [
        100, 95, 90, 85, 80,          # Down: 100 -> 80
        85, 90, 95, 100,              # Up: 80 -> 100 (+25%)
        95, 90, 85, 80, 75, 70,       # Down: 100 -> 70 (-30%)
        75, 80, 85, 90, 95, 100,      # Up: 70 -> 100 (+42.9%)
        95, 90, 85, 80,               # Down: 100 -> 80 (-20%)
        85, 90, 95, 100,              # Up: 80 -> 100 (+25%)
        95, 90                        # Down: 100 -> 90 (-10%)
    ]
    prices = [
        1,
        100, 95, 90, 85, 90, 85, 80,      # Down phase 100 -> 80
        85, 90, 95, 100,          # Up bounce (80 -> 100 = +25%)
        95, 90, 85, 80, 85, 80, 75, 70,   # Down bounce (100 -> 70 = -30%)
        75, 80, 85, 90, 100,          # Up bounce (70 -> 90 = +28.6%)
        100, 95, 90, 95, 95, 90, 85, 80,    # 100 -> 80
        80, 85, 95, 100,   # 80 -> 100
        90,               # 100 -> 90
        1000, 1
    ]
    print("100 -> 80 , 80 -> 100 , 100 -> 70 , 70 -> 100 , 100 -> 80 , 80 -> 100 , 100 -> 90")

    print("Expected: 100→80, 80→100, 100→70, 70→100, 100→80, 80→100, 100→90")

    for price in prices:
        state = detector.detect_bounce(price, up_bounce_threshold=1.1, down_bounce_threshold=0.9)

    print(f"\nTotal bounces detected: {len(state['bounce_list'])}")
    for i, bounce in enumerate(state['bounce_list']):
        print(f"  Bounce {i+1}: {bounce['type']:>4} | "
              f"{bounce['start']:6.2f} → {bounce['end']:6.2f} | "
              f"Gain: {bounce['gain']*100:+6.1f}%")

    print(f"\nMin price seen: {state['min']:.2f}")
    print(f"Max price seen: {state['max']:.2f}")


def test_no_bounce():
    """Test: Price moves but doesn't hit threshold"""
    print("\n=== TEST 3: No Bounce (Insufficient Movement) ===")
    detector = BounceDetector()

    # Price oscillates within ±5% (below the 10% threshold)
    prices = [100, 98, 96, 98, 100, 102, 104, 102, 100]

    for price in prices:
        state = detector.detect_bounce(price, up_bounce_threshold=1.1, down_bounce_threshold=0.9)

    print(f"Total bounces detected: {len(state['bounce_list'])}")
    direction = state['direction'] if state['direction'] else 'None'
    print(f"Direction: {direction}")
    print(f"Price range: {state['min']:.2f} - {state['max']:.2f}")


def test_edge_cases():
    """Test: Edge cases like same price, single price"""
    print("\n=== TEST 4: Edge Cases ===")

    # Test 1: Single price point
    detector1 = BounceDetector()
    state1 = detector1.detect_bounce(100)
    dir1 = state1['direction'] if state1['direction'] else 'None'
    print(f"Single price: Bounces={len(state1['bounce_list'])}, Direction={dir1}")

    # Test 2: Same price repeated
    detector2 = BounceDetector()
    for _ in range(5):
        state2 = detector2.detect_bounce(100)
    dir2 = state2['direction'] if state2['direction'] else 'None'
    print(f"Repeated price: Bounces={len(state2['bounce_list'])}, Direction={dir2}")

    # Test 3: Very large swing
    detector3 = BounceDetector()
    prices = [100, 50, 150]  # -50% then +200%
    for price in prices:
        state3 = detector3.detect_bounce(price, up_bounce_threshold=1.1, down_bounce_threshold=0.9)
    print(f"Large swings: Bounces={len(state3['bounce_list'])}")
    for bounce in state3['bounce_list']:
        print(f"  {bounce['type']}: {bounce['start']:.2f} → {bounce['end']:.2f} ({bounce['gain']*100:+.1f}%)")


def test_custom_thresholds():
    """Test: Different threshold values"""
    print("\n=== TEST 5: Custom Thresholds (5% bounce) ===")
    detector = BounceDetector()

    # Smaller movements should trigger with 5% threshold
    prices = [100, 98, 96, 94, 99, 104, 100, 95]

    for price in prices:
        state = detector.detect_bounce(price, up_bounce_threshold=1.05, down_bounce_threshold=0.95)

    print(f"Total bounces detected: {len(state['bounce_list'])}")
    for i, bounce in enumerate(state['bounce_list']):
        print(f"  Bounce {i+1}: {bounce['type']:>4} | "
              f"{bounce['start']:6.2f} → {bounce['end']:6.2f} | "
              f"Gain: {bounce['gain']*100:+6.1f}%")


def test_detailed_trace():
    """Test: Detailed trace of bounce detection"""
    print("\n=== TEST 6: Detailed Trace ===")
    detector = BounceDetector()
    prev_bounces = 0
    # Simple pattern: down then up
    prices = [100, 90, 80, 90, 100]
    print("Prices: 100 -> 90 -> 80 -> 90 -> 100")
    print("Expected: DOWN bounce (100->80), then UP bounce (80->100)\n")

    for i, price in enumerate(prices):
        state = detector.detect_bounce(price, up_bounce_threshold=1.1, down_bounce_threshold=0.9)
        direction = state['direction'] if state['direction'] else 'None'
        print(f"Step {i+1}: Price={price:6.2f} | Dir={direction:>5} | "
              f"Extreme={state['extreme']:6.2f} | Bounces={len(state['bounce_list'])}")

        # Show new bounces
        if i > 0 and len(state['bounce_list']) > prev_bounces:
            new_bounce = state['bounce_list'][-1]
            print(f"       >>> NEW BOUNCE: {new_bounce['type']} from "
                  f"{new_bounce['start']:.2f} to {new_bounce['end']:.2f} "
                  f"({new_bounce['gain']*100:+.1f}%)")

        prev_bounces = len(state['bounce_list'])


# Run all tests
if __name__ == "__main__":
    print("=" * 60)
    print("BOUNCE DETECTION TESTS")
    print("=" * 60)

    test_simple_up_bounce()
    test_multiple_bounces()
    test_no_bounce()
    test_edge_cases()
    test_custom_thresholds()
    test_detailed_trace()

    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETED")
    print("=" * 60)
