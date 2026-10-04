import sys
from router.config import load_tier_config, save_tier_config, TIER_MAP
from router.discovery import fetch_available_models, categorize_model, VENDOR_ORDER

def display_interactive_menu() -> None:
    tier_config = load_tier_config()
    models = fetch_available_models()
    grouped = {vendor: [] for vendor, _ in VENDOR_ORDER}
    for m in models:
        fam = categorize_model(m)
        grouped[fam].append(m)

    number_to_model = {}
    while True:
        print()
        print("======================================================================")
        print("  AVAILABLE CURSOR MODELS (GROUPED BY VENDOR)")
        print("======================================================================")
        number_to_model.clear()
        current_idx = 1

        for vendor, _ in VENDOR_ORDER:
            members = grouped.get(vendor, [])
            if not members:
                continue
            print()
            print(f"--- {vendor} ---")
            for m in members:
                number_to_model[str(current_idx)] = m
                print(f"  [{current_idx:2d}] {m}")
                current_idx += 1

        print()
        print("----------------------------------------------------------------------")
        print("Current Active Tiers:")
        for t in ('cheap', 'balanced', 'smart'):
            model = tier_config.get(t, 'auto')
            print(f"  [a{t:<8}] -> {model:<28}")
        print("======================================================================")

        try:
            tier_raw = input("👉 Enter tier to edit (a[c]heap / a[b]alanced / a[s]mart, or 'q' to exit): ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            sys.exit(0)

        if tier_raw in ('q', 'quit', 'exit', ''):
            print("Configuration saved.")
            sys.exit(0)

        if tier_raw not in TIER_MAP:
            print("⚠ Invalid tier. Choose 'c' (acheap), 'b' (abalanced), or 's' (asmart).")
            continue

        tier_choice = TIER_MAP[tier_raw]

        try:
            model_pick = input(f"👉 Enter model number for 'a{tier_choice}' [1..{len(number_to_model)}]: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            sys.exit(0)

        if model_pick in number_to_model:
            selected_model = number_to_model[model_pick]
            tier_config[tier_choice] = selected_model
            save_tier_config(tier_config)
            print(f"✓ Tier 'a{tier_choice}' updated to -> {selected_model}")
        else:
            print(f"⚠️ Invalid model selection: '{model_pick}'")
